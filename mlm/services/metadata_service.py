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

    def list_unmatched_files(self, limit: int = 500) -> list[dict]:
        """Return up to *limit* files with no entity link."""
        with get_connection() as conn:
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
        return [dict(r) for r in rows]

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
    # Internal helpers
    # ------------------------------------------------------------------

    def _match_movie(self, media_file_id: int, parsed, file_name: str) -> dict:
        results = self.tmdb.search_movie(parsed.title or "", parsed.year)
        best = (results.get("results") or [None])[0]
        if not best:
            log.info("No TMDB movie result for '%s'", parsed.title)
            return {"status": "unmatched", "reason": "No movie results"}

        details = self.tmdb.movie_details(best["id"])
        release = details.get("release_date") or ""
        entity_id = self.entities_repo.upsert_entity(
            media_type="movie",
            title=details.get("title") or parsed.title or file_name,
            release_year=int(release[:4]) if len(release) >= 4 else parsed.year,
            tmdb_id=details.get("id"),
            plot=details.get("overview"),
            rating=details.get("vote_average"),
            genres_json=json.dumps(details.get("genres", [])),
            poster_path=details.get("poster_path"),
            metadata_json=json.dumps(details),
        )
        self.entities_repo.link_file_to_entity(media_file_id, entity_id)
        log.info("Matched file_id=%d → movie '%s'", media_file_id, details.get("title"))
        return {"status": "matched", "media_type": "movie", "title": details.get("title")}

    def _match_episode(self, media_file_id: int, parsed, file_name: str) -> dict:
        results = self.tmdb.search_tv(parsed.show_title or "")
        best = (results.get("results") or [None])[0]
        if not best:
            log.info("No TMDB TV result for '%s'", parsed.show_title)
            return {"status": "unmatched", "reason": "No TV results"}

        details = self.tmdb.tv_details(best["id"])
        air_date = details.get("first_air_date") or ""
        entity_id = self.entities_repo.upsert_entity(
            media_type="show",
            title=details.get("name") or parsed.show_title or file_name,
            release_year=int(air_date[:4]) if len(air_date) >= 4 else None,
            tmdb_id=details.get("id"),
            plot=details.get("overview"),
            rating=details.get("vote_average"),
            genres_json=json.dumps(details.get("genres", [])),
            poster_path=details.get("poster_path"),
            metadata_json=json.dumps(details),
        )
        self.entities_repo.link_file_to_entity(media_file_id, entity_id)

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

        log.info(
            "Matched file_id=%d → show '%s' S%02dE%02d",
            media_file_id, details.get("name"),
            parsed.season_number or 0, parsed.episode_number or 0,
        )
        return {
            "status": "matched",
            "media_type": "show",
            "title": details.get("name"),
            "season": parsed.season_number,
            "episode": parsed.episode_number,
        }

    def manual_match_by_tmdb_id(
        self, media_file_id: int, tmdb_id: int, media_type: str
    ) -> dict:
        """Directly link *media_file_id* to a known TMDB id.

        Args:
            media_file_id: DB id of the media_files row.
            tmdb_id:       TMDB numeric identifier (must be > 0).
            media_type:    ``"movie"`` or ``"show"``.

        Raises:
            ValueError: if *tmdb_id* is invalid or *media_type* is unknown.
        """
        if tmdb_id <= 0:
            raise ValueError(f"tmdb_id must be a positive integer, got {tmdb_id}")
        if media_type not in {"movie", "show"}:
            raise ValueError(f"media_type must be 'movie' or 'show', got '{media_type}'")

        if media_type == "movie":
            details = self.tmdb.movie_details(tmdb_id)
            title = details.get("title")
            release = details.get("release_date") or ""
            year = int(release[:4]) if len(release) >= 4 else None
        else:
            details = self.tmdb.tv_details(tmdb_id)
            title = details.get("name")
            air_date = details.get("first_air_date") or ""
            year = int(air_date[:4]) if len(air_date) >= 4 else None

        entity_id = self.entities_repo.upsert_entity(
            media_type=media_type,
            title=title or f"TMDB {tmdb_id}",
            release_year=year,
            tmdb_id=tmdb_id,
            plot=details.get("overview"),
            rating=details.get("vote_average"),
            genres_json=json.dumps(details.get("genres", [])),
            poster_path=details.get("poster_path"),
            metadata_json=json.dumps(details),
        )
        self.entities_repo.link_file_to_entity(media_file_id, entity_id)
        log.info("Manual match: file_id=%d → %s tmdb_id=%d", media_file_id, media_type, tmdb_id)
        return {"status": "matched", "title": title, "tmdb_id": tmdb_id}
