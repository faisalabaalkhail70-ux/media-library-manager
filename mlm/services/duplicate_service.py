"""Detect exact and quality-variant media files.

Three group types:
  exact   — same bytes (size + partial hash + full hash match)
  quality — same TMDB entity + same episode, different resolution/file
  possible— fuzzy name/duration/size similarity, catch-all for the rest

'possible' rows that share a TMDB entity are now reclassified as
'quality' automatically, so the user sees a meaningful label.
"""
import logging
from collections import defaultdict

from mlm.db.connection import get_connection
from mlm.db.repositories.duplicates_repo import DuplicatesRepository
from mlm.db.repositories.files_repo import FilesRepository
from mlm.utils.hashing import partial_md5, full_md5
from mlm.utils.similarity import text_similarity, duration_similarity, size_similarity

log = logging.getLogger(__name__)

_MAX_SIZE_DIFF_BYTES      = 200 * 1024 * 1024   # 200 MB
_MAX_DURATION_DIFF_SECONDS = 120
_MIN_SCORE                = 0.85


class DuplicateService:
    def __init__(
        self,
        repo: DuplicatesRepository | None = None,
        files_repo: FilesRepository | None = None,
    ) -> None:
        self.repo = repo or DuplicatesRepository()
        self.files_repo = files_repo or FilesRepository()

    def _list_candidate_files(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, entity_id, file_name, file_path, file_size_bytes,
                       duration_seconds, partial_hash, full_hash,
                       resolution, video_codec
                FROM media_files
                WHERE removed_at IS NULL
                ORDER BY file_size_bytes DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def build_duplicate_groups(self) -> dict:
        files = self._list_candidate_files()
        self.repo.clear_groups()
        log.info("Building duplicate groups from %d candidate files", len(files))

        exact_groups   = self._build_exact_duplicates(files)
        quality_groups = self._build_quality_variants(files)
        # Exclude files already in an exact or quality group from fuzzy scan
        used_ids: set[int] = self._ids_in_groups()
        remaining = [f for f in files if f["id"] not in used_ids]
        possible_groups = self._build_possible_duplicates(remaining)

        log.info(
            "Scan complete: %d exact, %d quality-variant, %d possible",
            exact_groups, quality_groups, possible_groups,
        )
        return {
            "exact_groups":   exact_groups,
            "quality_groups": quality_groups,
            "possible_groups": possible_groups,
        }

    def _ids_in_groups(self) -> set[int]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT media_file_id FROM duplicate_items"
            ).fetchall()
        return {r[0] for r in rows}

    # ── Exact duplicates ─────────────────────────────────────────────────

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

    # ── Quality variants (same entity, different resolution) ────────────────

    def _build_quality_variants(self, files: list[dict]) -> int:
        """Group files that share the same media_entity_id (and thus represent
        the same movie or episode) but differ in file path / resolution.

        These are intentional quality upgrades/downgrades, not accidental
        copies — surfaced separately so the user can choose which to keep.
        """
        # Bucket by entity_id; also look at episodes rows for TV
        entity_buckets: dict[int, list[dict]] = defaultdict(list)
        for f in files:
            if f["entity_id"] is not None:
                entity_buckets[f["entity_id"]].append(f)

        # For TV shows, further split by (season, episode)
        # Pull episode rows for the files we care about
        file_ids = [f["id"] for f in files if f["entity_id"] is not None]
        ep_map: dict[int, tuple[int, int]] = {}   # file_id → (season, episode)
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

            # Sub-bucket: for TV by episode key, for movies treat all as one bucket
            sub_buckets: dict[tuple, list[dict]] = defaultdict(list)
            for f in members:
                key = ep_map.get(f["id"], (0, 0))   # (0,0) = movie / unlinked
                sub_buckets[key].append(f)

            for sub_members in sub_buckets.values():
                if len(sub_members) < 2:
                    continue
                # Skip if all files are identical in path (shouldn’t happen)
                if len({f["file_path"] for f in sub_members}) < 2:
                    continue
                score = 1.0  # definite — same TMDB entity
                gid = self.repo.create_group("quality", score)
                for item in sub_members:
                    self.repo.add_item(gid, item["id"], score, {
                        "reason": "same_entity_diff_file",
                        "resolution": item.get("resolution"),
                    })
                group_count += 1

        return group_count

    # ── Possible duplicates (fuzzy) ─────────────────────────────────────

    def _build_possible_duplicates(self, files: list[dict]) -> int:
        group_count  = 0
        used_pairs:  set[tuple[int, int]] = set()

        size_buckets: dict[int, list[dict]] = defaultdict(list)
        for f in files:
            bucket = f["file_size_bytes"] // (_MAX_SIZE_DIFF_BYTES // 2)
            size_buckets[bucket].append(f)
            size_buckets[bucket + 1].append(f)

        seen_in_bucket: set[tuple[int, int]] = set()
        for bucket_files in size_buckets.values():
            for i, a in enumerate(bucket_files):
                for b in bucket_files[i + 1:]:
                    pair_key = (min(a["id"], b["id"]), max(a["id"], b["id"]))
                    if pair_key in seen_in_bucket:
                        continue
                    seen_in_bucket.add(pair_key)

                    if abs(a["file_size_bytes"] - b["file_size_bytes"]) > _MAX_SIZE_DIFF_BYTES:
                        continue
                    if (a["duration_seconds"] and b["duration_seconds"] and
                            abs(a["duration_seconds"] - b["duration_seconds"]) > _MAX_DURATION_DIFF_SECONDS):
                        continue

                    name_score = text_similarity(a["file_name"], b["file_name"])
                    dur_score  = duration_similarity(a["duration_seconds"], b["duration_seconds"])
                    sz_score   = size_similarity(a["file_size_bytes"], b["file_size_bytes"])
                    score = round((name_score * 0.5) + (dur_score * 0.3) + (sz_score * 0.2), 3)

                    if score < _MIN_SCORE or pair_key in used_pairs:
                        continue
                    used_pairs.add(pair_key)

                    gid = self.repo.create_group("possible", score)
                    for item in (a, b):
                        self.repo.add_item(gid, item["id"], score, {
                            "name_score": name_score,
                            "duration_score": dur_score,
                            "size_score": sz_score,
                        })
                    group_count += 1

        return group_count

    # ── Hash helpers ─────────────────────────────────────────────────

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
