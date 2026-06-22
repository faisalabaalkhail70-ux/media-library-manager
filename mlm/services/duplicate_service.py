"""Detect exact and fuzzy-duplicate media files."""
import logging
from collections import defaultdict

from mlm.db.connection import get_connection
from mlm.db.repositories.duplicates_repo import DuplicatesRepository
from mlm.db.repositories.files_repo import FilesRepository
from mlm.utils.hashing import partial_md5, full_md5
from mlm.utils.similarity import text_similarity, duration_similarity, size_similarity

log = logging.getLogger(__name__)

# Files whose sizes differ by more than this are never fuzzy-duplicates.
_MAX_SIZE_DIFF_BYTES = 200 * 1024 * 1024   # 200 MB
# Files whose durations differ by more than this are never fuzzy-duplicates.
_MAX_DURATION_DIFF_SECONDS = 120
# Minimum weighted score to be considered a possible duplicate.
_MIN_SCORE = 0.85


class DuplicateService:
    """Build exact and possible-duplicate groups for all known media files."""

    def __init__(
        self,
        repo: DuplicatesRepository | None = None,
        files_repo: FilesRepository | None = None,
    ) -> None:
        self.repo = repo or DuplicatesRepository()
        self.files_repo = files_repo or FilesRepository()

    def _list_candidate_files(self) -> list[dict]:
        """Return all non-removed files ordered by descending size."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, file_name, file_path, file_size_bytes, duration_seconds,
                       partial_hash, full_hash, resolution, video_codec
                FROM media_files
                WHERE removed_at IS NULL
                ORDER BY file_size_bytes DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def build_duplicate_groups(self) -> dict:
        """Re-build all duplicate groups from scratch.

        Returns:
            ``{"exact_groups": int, "possible_groups": int}``
        """
        files = self._list_candidate_files()
        self.repo.clear_groups()
        log.info("Building duplicate groups from %d candidate files", len(files))
        exact_groups = self._build_exact_duplicates(files)
        possible_groups = self._build_possible_duplicates(files)
        log.info("Duplicate scan complete: %d exact, %d possible", exact_groups, possible_groups)
        return {"exact_groups": exact_groups, "possible_groups": possible_groups}

    # ------------------------------------------------------------------
    # Hash helpers (with lazy computation and DB persistence)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Exact duplicates — O(n) using nested hash buckets
    # ------------------------------------------------------------------

    def _build_exact_duplicates(self, files: list[dict]) -> int:
        """Group files with identical size + partial hash + full hash."""
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
                    group_id = self.repo.create_group("exact", 1.0)
                    for item in full_items:
                        self.repo.add_item(
                            group_id, item["id"], 1.0,
                            {"reason": "same_size_partial_full_hash"},
                        )
                    group_count += 1

        return group_count

    # ------------------------------------------------------------------
    # Possible duplicates — O(n²) with early-exit guards
    # Size-bucket pre-filter dramatically reduces iterations in practice.
    # ------------------------------------------------------------------

    def _build_possible_duplicates(self, files: list[dict]) -> int:
        """Find near-duplicate pairs using name + duration + size similarity."""
        group_count = 0
        used_pairs: set[tuple[int, int]] = set()

        # Pre-bucket by 200 MB size bands to reduce comparisons
        size_buckets: dict[int, list[dict]] = defaultdict(list)
        for f in files:
            bucket = f["file_size_bytes"] // (_MAX_SIZE_DIFF_BYTES // 2)
            size_buckets[bucket].append(f)
            # Also add to the adjacent bucket for cross-boundary matches
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
                    dur_score = duration_similarity(a["duration_seconds"], b["duration_seconds"])
                    sz_score = size_similarity(a["file_size_bytes"], b["file_size_bytes"])
                    score = round((name_score * 0.5) + (dur_score * 0.3) + (sz_score * 0.2), 3)

                    if score < _MIN_SCORE:
                        continue
                    if pair_key in used_pairs:
                        continue
                    used_pairs.add(pair_key)

                    group_id = self.repo.create_group("possible", score)
                    for item in (a, b):
                        self.repo.add_item(group_id, item["id"], score, {
                            "name_score": name_score,
                            "duration_score": dur_score,
                            "size_score": sz_score,
                        })
                    group_count += 1

        return group_count
