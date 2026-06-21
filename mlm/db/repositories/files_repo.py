from mlm.db.connection import get_connection


class FilesRepository:
    def upsert_file(
        self,
        *,
        directory_id: int,
        file_path: str,
        parent_folder: str,
        file_name: str,
        extension: str,
        file_size_bytes: int,
        modified_at: str | None,
    ) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO media_files (
                    directory_id, file_path, parent_folder, file_name,
                    extension, file_size_bytes, modified_at, removed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(file_path) DO UPDATE SET
                    parent_folder=excluded.parent_folder,
                    file_name=excluded.file_name,
                    extension=excluded.extension,
                    file_size_bytes=excluded.file_size_bytes,
                    modified_at=excluded.modified_at,
                    removed_at=NULL
                """,
                (
                    directory_id,
                    file_path,
                    parent_folder,
                    file_name,
                    extension,
                    file_size_bytes,
                    modified_at,
                ),
            )

    def save_hashes(
        self,
        *,
        file_path: str,
        partial_hash: str | None = None,
        full_hash: str | None = None,
        algo: str = "md5",
    ) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE media_files
                SET partial_hash = COALESCE(?, partial_hash),
                    full_hash    = COALESCE(?, full_hash),
                    hash_algo    = ?
                WHERE file_path = ?
                """,
                (partial_hash, full_hash, algo, file_path),
            )

    def mark_removed(self, file_path: str, removed_at: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE media_files
                SET removed_at = ?
                WHERE file_path = ? AND removed_at IS NULL
                """,
                (removed_at, file_path),
            )

    def get_known_paths_for_directory(self, directory_id: int) -> set[str]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT file_path FROM media_files
                WHERE directory_id = ? AND removed_at IS NULL
                """,
                (directory_id,),
            ).fetchall()
        return {row["file_path"] for row in rows}

    def fetch_library_rows(self, limit: int = 5000) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    mf.id,
                    mf.file_name,
                    mf.file_path,
                    mf.extension,
                    mf.file_size_bytes,
                    mf.modified_at,
                    mf.resolution,
                    mf.video_codec,
                    me.title AS matched_title,
                    me.release_year
                FROM media_files mf
                LEFT JOIN media_entities me ON me.id = mf.entity_id
                WHERE mf.removed_at IS NULL
                ORDER BY mf.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]