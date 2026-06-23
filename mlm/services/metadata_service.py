"""Metadata matching: parse filenames and look them up on TMDB."""
import json
import logging

from mlm.db.connection import get_connection
from mlm.db.repositories.entities_repo import EntitiesRepository
from mlm.integrations.tmdb_client import TMDBClient
from mlm.parsing.filename_parser import parse_media_filename

log = logging.getLogger(__name__)


class MetadataService:
    """Resolve media files to TMDB entities (movies or TV shows)."""

    def __init__(
        self,
        tmdb: TMDBClient | None = None,
        entities_repo: EntitiesRepository | None = None,
    ) -> None:
        self.tmdb = tmdb or TMDBClient()
        self.entities_repo = entities_repo or EntitiesRepository()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_unmatched_files(self, limit: int = 0) -> list[dict]:
        """Return files with no entity link. limit=0 means all."""
        with get_connection() as conn:
            if limit and limit > 0:
                rows = conn.execute(
                    """
                    SELECT id, file_name, file_path
                    FROM media_files
                    WHERE entity_id IS NULL AND removed_at IS NULL
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, file_name, file_path
                    FROM media_files
                    WHERE entity_id IS NULL AND removed_at IS NULL
                    ORDER BY id DESC
                    """
                ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Auto-matching
    # ------------------------------------------------------------------

    def auto_match_file(self, media_file_id: int, file_name: str) -> dict:
        """Parse *file_name*, search TMDB, and link the best result."""
        log.debug("Auto-matching file_id=%d name=%s", media_file_id, file_name)
        parsed = parse_media_filename(file_name)

        if parsed.media_type == "movie":
            return self._match_movie(media_file_id, parsed, file_name)

        if parsed.media_type == "episode":
            return self._match_episode(media_file_id, parsed, file_name)

        log.info("Skipped file_id=%d — unrecognised filename format", media_file_id)
        return {"status": "skipped", "reason": "Unknown filename format"}

    # ------------------------------------------------------------------
    # Shared upsert helper  (was duplicated verbatim in both matchers)
    # ------------------------------------------------------------------

    def _upsert_and_link(
        self,
        media_file_id: int,
        details: dict,
        media_type: str,
        title_key: str,
        date_key: str,
        fallback_title: str,
    ) -> int:
        """Upsert a TMDB entity and link it to *media_file_id*.

        Returns the entity_id.
        """
        date_str = details.get(date_key) or ""
        year = int(date_str[:4]) if len(date_str) >= 4 else None
        entity_id = self.entities_repo.upsert_entity(
            media_type=media_type,
            title=details.get(title_key) or fallback_title,
            release_year=year,
            tmdb_id=details.get("id"),
            plot=details.get("overview"),
            rating=details.get("vote_average"),
            genres_json=json.dumps(details.get("genres", [])),
            poster_path=details.get("poster_path"),
            metadata_json=json.dumps(details),
        )
        self.entities_repo.link_file_to_entity(media_file_id, entity_id)
        return entity_id

    # ------------------------------------------------------------------
    # Movie matching
    # ------------------------------------------------------------------

    def _match_movie(self, media_file_id: int, parsed, file_name: str) -> dict:
        results = self.tmdb.search_movie(parsed.title or "", parsed.year)
        result_list = results.get("results") or []
        if not result_list:
            log.info("No TMDB movie result for '%s'", parsed.title)
            return {"status": "unmatched", "reason": "No movie results"}

        details = self.tmdb.movie_details(result_list[0]["id"])
        fallback = parsed.title or file_name
        entity_id = self._upsert_and_link(
            media_file_id, details, "movie", "title", "release_date", fallback
        )
        title = details.get("title")
        log.info("Matched file_id=%d → movie '%s'", media_file_id, title)
        return {"status": "matched", "media_type": "movie", "title": title}

    # ------------------------------------------------------------------
    # TV / episode matching
    # ------------------------------------------------------------------

    def _match_episode(self, media_file_id: int, parsed, file_name: str) -> dict:
        results = self.tmdb.search_tv(parsed.show_title or "")
        result_list = results.get("results") or []
        if not result_list:
            log.info("No TMDB TV result for '%s'", parsed.show_title)
            return {"status": "unmatched", "reason": "No TV results"}

        details = self.tmdb.tv_details(result_list[0]["id"])
        fallback = parsed.show_title or file_name
        entity_id = self._upsert_and_link(
            media_file_id, details, "show", "name", "first_air_date", fallback
        )

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO episodes (
                    entity_id, media_file_id, season_number, episode_number, is_missing
                )
                VALUES (?, ?, ?, ?, 0)
                ON CONFLICT(entity_id, season_number, episode_number)
                DO UPDATE SET media_file_id = excluded.media_file_id, is_missing = 0
                """,
                (entity_id, media_file_id, parsed.season_number, parsed.episode_number),
            )

        title = details.get("name")
        log.info(
            "Matched file_id=%d → show '%s' S%02dE%02d",
            media_file_id, title,
            parsed.season_number or 0, parsed.episode_number or 0,
        )
        return {
            "status": "matched",
            "media_type": "show",
            "title": title,
            "season": parsed.season_number,
            "episode": parsed.episode_number,
        }

    # ------------------------------------------------------------------
    # Manual / refresh operations
    # ------------------------------------------------------------------

    def manual_match_by_tmdb_id(
        self, media_file_id: int, tmdb_id: int, media_type: str
    ) -> dict:
        if tmdb_id <= 0:
            raise ValueError(f"tmdb_id must be a positive integer, got {tmdb_id}")
        if media_type not in {"movie", "show"}:
            raise ValueError(f"media_type must be 'movie' or 'show', got '{media_type}'")

        if media_type == "movie":
            details = self.tmdb.movie_details(tmdb_id)
            title_key, date_key = "title", "release_date"
        else:
            details = self.tmdb.tv_details(tmdb_id)
            title_key, date_key = "name", "first_air_date"

        entity_id = self._upsert_and_link(
            media_file_id, details, media_type, title_key, date_key,
            fallback_title=f"TMDB {tmdb_id}",
        )
        title = details.get(title_key)
        log.info("Manual match: file_id=%d → %s tmdb_id=%d", media_file_id, media_type, tmdb_id)
        return {"status": "matched", "title": title, "tmdb_id": tmdb_id}

    def refresh_entity(self, entity_id: int) -> dict:
        """Re-fetch TMDB metadata for an existing entity and update the DB.

        Used by the \"Refresh Metadata\" button in MoviesView.
        Returns a dict with 'status', 'title', and 'tmdb_id'.
        Raises ValueError if the entity is not found or has no tmdb_id.
        """
        with get_connection() as conn:
            row = conn.execute(
                "SELECT tmdb_id, media_type, title FROM media_entities WHERE id = ?",
                (entity_id,),
            ).fetchone()

        if row is None:
            raise ValueError(f"Entity id={entity_id} not found in database.")

        tmdb_id    = row["tmdb_id"]
        media_type = row["media_type"]
        title      = row["title"]

        if not tmdb_id:
            raise ValueError(
                f"Entity '{title}' (id={entity_id}) has no TMDB id — "
                "use Manual Match first before refreshing."
            )

        if media_type == "movie":
            details   = self.tmdb.movie_details(tmdb_id)
            title_key = "title"
            date_key  = "release_date"
        else:
            details   = self.tmdb.tv_details(tmdb_id)
            title_key = "name"
            date_key  = "first_air_date"

        new_title   = details.get(title_key) or title
        date_str    = details.get(date_key) or ""
        year        = int(date_str[:4]) if len(date_str) >= 4 else None
        rating      = details.get("vote_average")
        genres_json = json.dumps(details.get("genres", []))
        poster      = details.get("poster_path")
        plot        = details.get("overview")
        meta_json   = json.dumps(details)

        with get_connection() as conn:
            conn.execute(
                """
                UPDATE media_entities
                SET title = ?, release_year = ?, rating = ?,
                    genres_json = ?, poster_path = ?,
                    plot = ?, metadata_json = ?
                WHERE id = ?
                """,
                (new_title, year, rating, genres_json, poster, plot, meta_json, entity_id),
            )

        log.info("Refreshed metadata for entity_id=%d ('%s')", entity_id, new_title)
        return {"status": "refreshed", "title": new_title, "tmdb_id": tmdb_id}
