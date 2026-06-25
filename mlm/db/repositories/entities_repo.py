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
        """Insert or update a media entity atomically and return its id.

        Uses INSERT ... ON CONFLICT DO UPDATE (a.k.a. "upsert") so the
        operation is a single atomic statement.  The previous SELECT-then-
        INSERT/UPDATE two-step was susceptible to a race condition where two
        threads could both observe 'not found' and both attempt an INSERT,
        causing a UNIQUE constraint violation (issue #5).
        """
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO media_entities (
                    media_type, title, release_year, tmdb_id, plot, rating,
                    genres_json, poster_path, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(media_type, tmdb_id) DO UPDATE SET
                    title         = excluded.title,
                    release_year  = excluded.release_year,
                    plot          = excluded.plot,
                    rating        = excluded.rating,
                    genres_json   = excluded.genres_json,
                    poster_path   = excluded.poster_path,
                    metadata_json = excluded.metadata_json,
                    updated_at    = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (
                    media_type, title, release_year, tmdb_id,
                    plot, rating, genres_json, poster_path, metadata_json,
                ),
            )
            row = cur.fetchone()
            return int(row["id"])

    def link_file_to_entity(self, media_file_id: int, entity_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE media_files SET entity_id = ? WHERE id = ?",
                (entity_id, media_file_id),
            )
