from mlm.db.connection import get_connection


class EpisodesRepository:
    def list_show_entities(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, tmdb_id
                FROM media_entities
                WHERE media_type = 'show' AND tmdb_id IS NOT NULL
                ORDER BY title
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def existing_episode_keys(self, entity_id: int) -> set[tuple[int, int]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT season_number, episode_number
                FROM episodes
                WHERE entity_id = ? AND is_missing = 0
                """,
                (entity_id,),
            ).fetchall()
        return {(int(r["season_number"]), int(r["episode_number"])) for r in rows}

    def upsert_missing_episode(
        self,
        entity_id: int,
        season_number: int,
        episode_number: int,
        episode_title: str | None,
        air_date: str | None,
        tmdb_episode_id: int | None,
    ) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO episodes (
                    entity_id, media_file_id, season_number, episode_number,
                    episode_title, air_date, tmdb_episode_id, is_missing
                )
                VALUES (?, NULL, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(entity_id, season_number, episode_number)
                DO UPDATE SET
                    episode_title = excluded.episode_title,
                    air_date = excluded.air_date,
                    tmdb_episode_id = excluded.tmdb_episode_id,
                    is_missing = 1
                """,
                (
                    entity_id,
                    season_number,
                    episode_number,
                    episode_title,
                    air_date,
                    tmdb_episode_id,
                ),
            )

    def clear_missing_for_entity(self, entity_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                DELETE FROM episodes
                WHERE entity_id = ? AND is_missing = 1
                """,
                (entity_id,),
            )

    def fetch_missing_rows(self, entity_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    ep.entity_id,
                    me.title AS show_title,
                    ep.season_number,
                    ep.episode_number,
                    ep.episode_title,
                    ep.air_date,
                    ep.is_missing
                FROM episodes ep
                JOIN media_entities me ON me.id = ep.entity_id
                WHERE ep.entity_id = ? AND ep.is_missing = 1
                ORDER BY ep.season_number, ep.episode_number
                """,
                (entity_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def fetch_all_missing_rows(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    ep.entity_id,
                    me.title AS show_title,
                    ep.season_number,
                    ep.episode_number,
                    ep.episode_title,
                    ep.air_date,
                    ep.is_missing
                FROM episodes ep
                JOIN media_entities me ON me.id = ep.entity_id
                WHERE ep.is_missing = 1
                ORDER BY me.title, ep.season_number, ep.episode_number
                """
            ).fetchall()
        return [dict(r) for r in rows]