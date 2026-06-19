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