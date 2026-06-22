"""Detect exact and quality-variant media files.

Three group types
  exact    — identical bytes (size + partial_hash + full_hash)
  quality  — same TMDB entity + same episode code + different file path / resolution
  possible — same episode code OR same name, clearly different quality/folder

Scoring for 'possible'
  - name_score  (0.70 weight): normalised title only (strip codec/quality/group tags)
  - quality_tag (0.30 weight): bonus when quality tags differ (different encode of same ep)
  Duration is deliberately NOT used as a scoring factor — TV episodes of the same
  show routinely share runtime within seconds of each other.

Key guards
  1. Episode-code guard  : only pair files that share the same SxxExx code
  2. Same-folder guard   : files in the same folder are almost certainly different episodes
  3. Size guard          : >500 MB difference → very unlikely to be same content
"""
import logging
import re
from collections import defaultdict

from mlm.db.connection import get_connection
from mlm.db.repositories.duplicates_repo import DuplicatesRepository
from mlm.db.repositories.files_repo import FilesRepository
from mlm.utils.hashing import partial_md5, full_md5
from mlm.utils.similarity import text_similarity, same_episode

log = logging.getLogger(__name__)

_MAX_SIZE_DIFF_BYTES = 500 * 1024 * 1024   # 500 MB
_MIN_NAME_SCORE      = 0.70                 # minimum normalised title similarity

# Tags stripped before name comparison
_STRIP_RE = re.compile(
    r"\b("
    r"bluray|blu-ray|bdrip|brrip|webrip|web-dl|web|hdtv|dvdrip|dvd|"
    r"1080p|720p|480p|2160p|4k|uhd|"
    r"x264|x265|h264|h265|hevc|avc|xvid|divx|"
    r"aac|ac3|dts|ddp|atmos|truehd|flac|mp3|"
    r"remux|repack|proper|extended|theatrical|"
    r"yts|rarbg|ettv|ion10|glhf|smurf|kontrast|ntg|bia|cm"
    r")\b",
    re.IGNORECASE,
)
_QUALITY_TAGS = re.compile(
    r"\b(1080p|720p|480p|2160p|4k|uhd|bluray|blu-ray|webrip|web-dl|hdtv|bdrip)\b",
    re.IGNORECASE,
)


def _normalise(name: str) -> str:
    """Strip codec/quality/group tokens so only title+episode code remain."""
    name = name.rsplit(".", 1)[0]           # drop extension
    name = name.replace(".", " ").replace("_", " ")
    name = _STRIP_RE.sub("", name)
    name = re.sub(r"\s{2,}", " ", name).strip().lower()
    return name


def _quality_tags_set(name: str) -> set[str]:
    return {m.group(0).lower() for m in _QUALITY_TAGS.finditer(name)}


class DuplicateService:
    def __init__(
        self,
        repo: DuplicatesRepository | None = None,
        files_repo: FilesRepository | None = None,
    ) -> None:
        self.repo       = repo or DuplicatesRepository()
        self.files_repo = files_repo or FilesRepository()

    def _list_candidate_files(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, entity_id, file_name, file_path, file_size_bytes,
                       duration_seconds, partial_hash, full_hash,
                       resolution, video_codec, parent_folder
                FROM media_files
                WHERE removed_at IS NULL
                ORDER BY file_size_bytes DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def build_duplicate_groups(self) -> dict:
        files = self._list_candidate_files()
        self.repo.clear_non_ignored_groups()
        log.info("Building duplicate groups from %d candidate files", len(files))

        exact_groups   = self._build_exact_duplicates(files)
        quality_groups = self._build_quality_variants(files)
        used_ids       = self._ids_in_groups()
        remaining      = [f for f in files if f["id"] not in used_ids]
        possible_groups = self._build_possible_duplicates(remaining)

        log.info(
            "Scan complete: %d exact, %d quality-variant, %d possible",
            exact_groups, quality_groups, possible_groups,
        )
        return {
            "exact_groups":    exact_groups,
            "quality_groups":  quality_groups,
            "possible_groups": possible_groups,
        }

    def _ids_in_groups(self) -> set[int]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT media_file_id FROM duplicate_items"
            ).fetchall()
        return {r[0] for r in rows}

    # ── Exact duplicates ───────────────────────────────────────────────────

    def _build_exact_duplicates(self, files: list[dict]) -> int:
        by_size: dict[int, list[dict]] = defaultdict(list)
        for row in files:
            by_size[row["file_size_bytes"]].append(row)

        group_count = 0
        for items in by_size.values():
            if len(items) < 2:
                continue
            by_partial: dict[str, list[dict]] = defaultdict(list)
            for item in items:
                try:
                    by_partial[self._compute_partial(item)].append(item)
                except OSError as exc:
                    log.warning("Cannot hash %s: %s", item["file_path"], exc)

            for partial_items in by_partial.values():
                if len(partial_items) < 2:
                    continue
                by_full: dict[str, list[dict]] = defaultdict(list)
                for item in partial_items:
                    try:
                        by_full[self._compute_full(item)].append(item)
                    except OSError as exc:
                        log.warning("Cannot full-hash %s: %s", item["file_path"], exc)

                for full_items in by_full.values():
                    if len(full_items) < 2:
                        continue
                    gid = self.repo.create_group("exact", 1.0)
                    for item in full_items:
                        self.repo.add_item(gid, item["id"], 1.0, {"reason": "identical"})
                    group_count += 1

        return group_count

    # ── Quality variants ────────────────────────────────────────────────
    # Same entity + same episode code + different file path (different encode/source)

    def _build_quality_variants(self, files: list[dict]) -> int:
        entity_buckets: dict[int, list[dict]] = defaultdict(list)
        for f in files:
            if f["entity_id"] is not None:
                entity_buckets[f["entity_id"]].append(f)

        file_ids = [f["id"] for f in files if f["entity_id"] is not None]
        ep_map: dict[int, tuple[int, int]] = {}
        if file_ids:
            placeholders = ",".join("?" * len(file_ids))
            with get_connection() as conn:
                rows = conn.execute(
                    f"""
                    SELECT media_file_id, season_number, episode_number
                    FROM episodes
                    WHERE media_file_id IN ({placeholders}) AND is_missing = 0
                    """,
                    file_ids,
                ).fetchall()
            for r in rows:
                ep_map[r["media_file_id"]] = (r["season_number"], r["episode_number"])

        group_count = 0
        for entity_id, members in entity_buckets.items():
            if len(members) < 2:
                continue

            sub_buckets: dict[tuple, list[dict]] = defaultdict(list)
            for f in members:
                key = ep_map.get(f["id"], (0, 0))
                sub_buckets[key].append(f)

            for sub_members in sub_buckets.values():
                if len(sub_members) < 2:
                    continue
                if len({f["file_path"] for f in sub_members}) < 2:
                    continue
                # Only flag as quality-variant if resolution/codec actually differs
                resolutions = {f.get("resolution") for f in sub_members if f.get("resolution")}
                codecs      = {f.get("video_codec") for f in sub_members if f.get("video_codec")}
                if len(resolutions) < 2 and len(codecs) < 2:
                    continue
                gid = self.repo.create_group("quality", 1.0)
                for item in sub_members:
                    self.repo.add_item(gid, item["id"], 1.0, {
                        "reason": "same_entity_diff_quality",
                        "resolution": item.get("resolution"),
                        "codec": item.get("video_codec"),
                    })
                group_count += 1

        return group_count

    # ── Possible duplicates (name + quality tag based) ─────────────────────
    # Pairs files with the SAME episode code that differ in quality/folder.
    # Duration is NOT used — TV episodes share runtimes too easily.

    def _build_possible_duplicates(self, files: list[dict]) -> int:
        group_count  = 0
        used_pairs:  set[tuple[int, int]] = set()
        ignored_ids  = self._ignored_file_ids()

        # Index files by their SxxExx code so we only compare same-episode pairs
        ep_code_re = re.compile(r"[Ss](\d{1,2})[Ee](\d{1,2})")
        ep_buckets: dict[str, list[dict]] = defaultdict(list)
        no_code: list[dict] = []

        for f in files:
            if f["id"] in ignored_ids:
                continue
            m = ep_code_re.search(f["file_name"])
            if m:
                ep_buckets[m.group(0).upper()].append(f)
            else:
                no_code.append(f)

        def _check_pair(a: dict, b: dict) -> None:
            nonlocal group_count
            pair_key = (min(a["id"], b["id"]), max(a["id"], b["id"]))
            if pair_key in used_pairs:
                return

            # Guard: same parent folder → different episodes of the same show
            if (a.get("parent_folder") and b.get("parent_folder") and
                    a["parent_folder"] == b["parent_folder"]):
                return

            # Guard: size too different
            if abs(a["file_size_bytes"] - b["file_size_bytes"]) > _MAX_SIZE_DIFF_BYTES:
                return

            # Name similarity on normalised title
            norm_a = _normalise(a["file_name"])
            norm_b = _normalise(b["file_name"])
            name_score = text_similarity(norm_a, norm_b)
            if name_score < _MIN_NAME_SCORE:
                return

            # Quality-tag bonus: different quality tags → likely different encodes
            tags_a = _quality_tags_set(a["file_name"])
            tags_b = _quality_tags_set(b["file_name"])
            quality_diff = 1.0 if tags_a != tags_b else 0.0

            score = round((name_score * 0.70) + (quality_diff * 0.30), 3)
            if score < _MIN_NAME_SCORE:
                return

            used_pairs.add(pair_key)
            gid = self.repo.create_group("possible", score)
            for item in (a, b):
                self.repo.add_item(gid, item["id"], score, {
                    "name_score":   name_score,
                    "quality_diff": quality_diff,
                    "tags_a":       list(tags_a),
                    "tags_b":       list(tags_b),
                })
            group_count += 1

        # Compare within same episode code buckets
        for bucket_files in ep_buckets.values():
            for i, a in enumerate(bucket_files):
                for b in bucket_files[i + 1:]:
                    _check_pair(a, b)

        # For files without an episode code (movies), compare all pairs
        for i, a in enumerate(no_code):
            for b in no_code[i + 1:]:
                _check_pair(a, b)

        return group_count

    def _ignored_file_ids(self) -> set[int]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT di.media_file_id
                FROM duplicate_items di
                JOIN duplicate_groups dg ON dg.id = di.group_id
                WHERE dg.review_status = 'ignored'
                """
            ).fetchall()
        return {r[0] for r in rows}

    def _compute_partial(self, item: dict) -> str:
        if item["partial_hash"]:
            return item["partial_hash"]
        h = partial_md5(item["file_path"])
        self.files_repo.save_hashes(file_path=item["file_path"], partial_hash=h)
        item["partial_hash"] = h
        return h

    def _compute_full(self, item: dict) -> str:
        if item["full_hash"]:
            return item["full_hash"]
        h = full_md5(item["file_path"])
        self.files_repo.save_hashes(file_path=item["file_path"], full_hash=h)
        item["full_hash"] = h
        return h
