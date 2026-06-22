"""Episode service: compares local files against TMDB season data.

Bug fixed: previously, existing_episode_keys() only returned episodes
that have a matching row in the `episodes` table with is_missing=0.
Files that were scanned but never had their episode metadata linked
(i.e. they exist in media_files but have no row in episodes at all)
were invisible to the check, causing ALL episodes to be reported
as missing even though one was present on disk.

Fix: we now build the existing-keys set from two sources:
  1. The episodes table (is_missing=0) — already linked episodes.
  2. media_files rows that belong to this entity and whose
     season/episode numbers were parsed at scan time — files that
     are present on disk but not yet linked in the episodes table.
"""
import logging

from mlm.db.connection import get_connection
from mlm.db.repositories.episodes_repo import EpisodesRepository
from mlm.integrations.tmdb_client import TMDBClient

log = logging.getLogger(__name__)


class EpisodeService:
    def __init__(self) -> None:
        self.repo = EpisodesRepository()
        self.tmdb = TMDBClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_show_missing(self, entity_id: int, tmdb_id: int) -> dict:
        """Compare local files against TMDB and persist missing episodes."""
        self.repo.clear_missing_for_entity(entity_id)
        existing = self._existing_episode_keys(entity_id)

        show = self.tmdb.tv_details(tmdb_id)
        total_missing = 0
        seasons_checked = 0

        for season in show.get("seasons", []):
            season_number = season.get("season_number")
            if season_number is None or season_number == 0:
                continue

            season_payload = self.tmdb.tv_season_details(tmdb_id, season_number)
            seasons_checked += 1

            for ep in season_payload.get("episodes", []):
                key = (season_number, int(ep.get("episode_number", 0)))
                if key not in existing:
                    self.repo.upsert_missing_episode(
                        entity_id=entity_id,
                        season_number=season_number,
                        episode_number=key[1],
                        episode_title=ep.get("name"),
                        air_date=ep.get("air_date"),
                        tmdb_episode_id=ep.get("id"),
                    )
                    total_missing += 1

        log.debug(
            "show entity_id=%d tmdb_id=%d: %d seasons checked, %d missing",
            entity_id, tmdb_id, seasons_checked, total_missing,
        )
        return {
            "show_title": show.get("name"),
            "seasons_checked": seasons_checked,
            "missing_count": total_missing,
        }

    def check_all_shows(self) -> list[dict]:
        results = []
        for show in self.repo.list_show_entities():
            results.append(self.check_show_missing(show["id"], show["tmdb_id"]))
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _existing_episode_keys(self, entity_id: int) -> set[tuple[int, int]]:
        """Return (season, episode) pairs that are present on disk for *entity_id*.

        Combines two sources so we never miss a file:

        1. ``episodes`` table rows with ``is_missing = 0``
           (episodes that were explicitly linked after metadata matching).

        2. ``media_files`` rows whose ``entity_id`` matches AND that carry
           parsed season/episode numbers (files on disk that have not yet
           been linked into the episodes table).
        """
        keys: set[tuple[int, int]] = set()

        # Source 1 — linked episode rows
        keys.update(self.repo.existing_episode_keys(entity_id))

        # Source 2 — media_files with parsed season/episode numbers
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT season_number, episode_number
                FROM media_files
                WHERE entity_id = ?
                  AND removed_at IS NULL
                  AND season_number IS NOT NULL
                  AND episode_number IS NOT NULL
                """,
                (entity_id,),
            ).fetchall()

        for row in rows:
            keys.add((int(row["season_number"]), int(row["episode_number"])))

        return keys
