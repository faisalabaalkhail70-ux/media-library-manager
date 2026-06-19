from collections import defaultdict
from mlm.db.connection import get_connection
from mlm.db.repositories.duplicates_repo import DuplicatesRepository
from mlm.utils.hashing import partial_md5, full_md5
from mlm.utils.similarity import text_similarity, duration_similarity, size_similarity

class DuplicateService:
    def __init__(self) -> None:
        self.repo = DuplicatesRepository()

    def _list_candidate_files(self) -> list[dict]:
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
        files = self._list_candidate_files()
        self.repo.clear_groups()

        exact_groups = self._build_exact_duplicates(files)
        possible_groups = self._build_possible_duplicates(files)

        return {
            "exact_groups": exact_groups,
            "possible_groups": possible_groups,
        }

    def _build_exact_duplicates(self, files: list[dict]) -> int:
        by_size = defaultdict(list)
        for row in files:
            by_size[row["file_size_bytes"]].append(row)

        group_count = 0

        for _, items in by_size.items():
            if len(items) < 2:
                continue

            by_partial = defaultdict(list)
            for item in items:
                item["partial_hash"] = item["partial_hash"] or partial_md5(item["file_path"])
                by_partial[item["partial_hash"]].append(item)

            for _, partial_items in by_partial.items():
                if len(partial_items) < 2:
                    continue

                by_full = defaultdict(list)
                for item in partial_items:
                    item["full_hash"] = item["full_hash"] or full_md5(item["file_path"])
                    by_full[item["full_hash"]].append(item)

                for _, full_items in by_full.items():
                    if len(full_items) < 2:
                        continue

                    group_id = self.repo.create_group("exact", 1.0)
                    for item in full_items:
                        self.repo.add_item(
                            group_id,
                            item["id"],
                            1.0,
                            {"reason": "same_size_partial_full_hash"},
                        )
                    group_count += 1

        return group_count

    def _build_possible_duplicates(self, files: list[dict]) -> int:
        group_count = 0
        used_pairs = set()

        for i, a in enumerate(files):
            for b in files[i + 1:]:
                if abs(a["file_size_bytes"] - b["file_size_bytes"]) > 200 * 1024 * 1024:
                    continue

                name_score = text_similarity(a["file_name"], b["file_name"])
                dur_score = duration_similarity(a["duration_seconds"], b["duration_seconds"])
                sz_score = size_similarity(a["file_size_bytes"], b["file_size_bytes"])
                score = round((name_score * 0.5) + (dur_score * 0.3) + (sz_score * 0.2), 3)

                if score < 0.85:
                    continue

                pair_key = tuple(sorted((a["id"], b["id"])))
                if pair_key in used_pairs:
                    continue
                used_pairs.add(pair_key)

                group_id = self.repo.create_group("possible", score)
                self.repo.add_item(group_id, a["id"], score, {
                    "name_score": name_score,
                    "duration_score": dur_score,
                    "size_score": sz_score,
                })
                self.repo.add_item(group_id, b["id"], score, {
                    "name_score": name_score,
                    "duration_score": dur_score,
                    "size_score": sz_score,
                })
                group_count += 1

        return group_count