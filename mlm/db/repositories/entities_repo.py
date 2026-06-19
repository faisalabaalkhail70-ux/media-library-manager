from mlm.db.connection import get_connection

class EntitiesRepository:
    def upsert_entity(
        self,
        *,
        media_type: str,
        title: str,
        release_year: int | None,
        tmdb_id: int | None,
        plot: str | None = None,
        rating: float | None = None,
        genres_json: str | None = None,
        poster_path: str | None = None,
        metadata_json: str | None = None,
    ) -> int:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id FROM media_entities
                WHERE media_type = ? AND tmdb_id IS ?
                """,
                (media_type, tmdb_id),
            ).fetchone()

            if row:
                conn.execute(
                    """
                    UPDATE media_entities
                    SET title=?, release_year=?, plot=?, rating=?, genres_json=?,
                        poster_path=?, metadata_json=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (title, release_year, plot, rating, genres_json, poster_path, metadata_json, row["id"]),
                )
                return int(row["id"])

            cur = conn.execute(
                """
                INSERT INTO media_entities (
                    media_type, title, release_year, tmdb_id, plot, rating,
                    genres_json, poster_path, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (media_type, title, release_year, tmdb_id, plot, rating, genres_json, poster_path, metadata_json),
            )
            return int(cur.lastrowid)

    def link_file_to_entity(self, media_file_id: int, entity_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE media_files SET entity_id = ? WHERE id = ?",
                (entity_id, media_file_id),
            )