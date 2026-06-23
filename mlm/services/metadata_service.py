"""Metadata matching service — links media files to TMDB entities.

Changes in v1.1
---------------
* _upsert_and_link() helper extracted — eliminates copy-paste between
  _match_movie and _match_episode (issue #7).
* Fragile (results.get('results') or [None])[0] pattern replaced with
  an explicit guard that returns early with a clear status dict (issue #12).
* Auto-matcher now skips entities already marked manually_verified=1 so
  user overrides set via MetadataEditorDialog are never clobbered.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from mlm.db.repositories.entities_repo import EntitiesRepository
from mlm.db.repositories.media_files_repo import MediaFilesRepository
from mlm.integrations.tmdb_client import TMDBClient
from mlm.utils.filename_parser import parse_filename

log = logging.getLogger(__name__)


class MetadataService:
    """Attempts to match unmatched media files against TMDB."""

    def __init__(
        self,
        tmdb: TMDBClient | None = None,
        entities_repo: EntitiesRepository | None = None,
        files_repo: MediaFilesRepository | None = None,
    ) -> None:
        self.tmdb          = tmdb or TMDBClient()
        self.entities_repo = entities_repo or EntitiesRepository()
        self.files_repo    = files_repo or MediaFilesRepository()

    # ------------------------------------------------------------------
    # Shared helper
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
        """Upsert a TMDB entity and link it to *media_file_id*."""
        date_str = details.get(date_key) or ""
        year: int | None = int(date_str[:4]) if len(date_str) >= 4 else None
        entity_id = self.entities_repo.upsert_entity(
            media_type    = media_type,
            title         = details.get(title_key) or fallback_title,
            release_year  = year,
            tmdb_id       = details.get("id"),
            plot          = details.get("overview"),
            rating        = details.get("vote_average"),
            genres_json   = json.dumps(details.get("genres") or []),
            poster_path   = details.get("poster_path"),
            metadata_json = json.dumps(details),
        )
        self.entities_repo.link_file_to_entity(media_file_id, entity_id)
        return entity_id

    # ------------------------------------------------------------------
    # Matching entry-points
    # ------------------------------------------------------------------

    def match_file(self, media_file_id: int) -> dict:
        """Attempt to match a single file against TMDB."""
        row = self.files_repo.get_by_id(media_file_id)
        if not row:
            return {"status": "error", "reason": "file not found"}

        if row.get("entity_id"):
            entity = self.entities_repo.get_by_id(row["entity_id"])
            if entity and entity.get("manually_verified"):
                log.debug(
                    "Skipping manually-verified entity_id=%d for file_id=%d",
                    row["entity_id"], media_file_id,
                )
                return {"status": "skipped", "reason": "manually verified"}

        file_name  = Path(row["file_path"]).stem
        parsed     = parse_filename(file_name)
        media_type = parsed.get("media_type", "movie")

        if media_type == "movie":
            return self._match_movie(media_file_id, parsed, file_name)
        return self._match_episode(media_file_id, parsed, file_name)

    def _match_movie(self, media_file_id: int, parsed: dict, fallback: str) -> dict:
        results     = self.tmdb.search_movie(
            parsed.get("title") or fallback, year=parsed.get("year")
        )
        result_list = results.get("results") or []
        if not result_list:
            return {"status": "unmatched", "reason": "No movie results from TMDB"}
        details = self.tmdb.get_movie_details(result_list[0]["id"])
        self._upsert_and_link(
            media_file_id, details, "movie", "title", "release_date", fallback
        )
        return {"status": "matched", "title": details.get("title")}

    def _match_episode(self, media_file_id: int, parsed: dict, fallback: str) -> dict:
        results     = self.tmdb.search_tv(parsed.get("title") or fallback)
        result_list = results.get("results") or []
        if not result_list:
            return {"status": "unmatched", "reason": "No TV results from TMDB"}
        details = self.tmdb.get_tv_details(result_list[0]["id"])
        self._upsert_and_link(
            media_file_id, details, "show", "name", "first_air_date", fallback
        )
        return {"status": "matched", "title": details.get("name")}
