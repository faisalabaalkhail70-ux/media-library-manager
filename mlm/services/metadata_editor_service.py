"""Metadata editor service — manual overrides & re-search on TMDB.

All writes stamp `manually_verified = 1` and `updated_at` on the entity
row so the auto-matcher never silently overwrites user corrections.
"""
import json
import logging
from datetime import datetime

from mlm.db.connection import get_connection
from mlm.integrations.tmdb_client import TMDBClient

log = logging.getLogger(__name__)


class MetadataEditorService:
    """Read / write metadata for a single media entity."""

    def __init__(self, tmdb: TMDBClient | None = None) -> None:
        self.tmdb = tmdb or TMDBClient()

    # ── Read ──────────────────────────────────────────────────────────

    def get_entity(self, entity_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM media_entities WHERE id = ?", (entity_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_entity_for_file(self, media_file_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT me.* FROM media_entities me
                JOIN media_files mf ON mf.entity_id = me.id
                WHERE mf.id = ?
                """,
                (media_file_id,),
            ).fetchone()
        return dict(row) if row else None

    # ── TMDB re-search ────────────────────────────────────────────────

    def search_tmdb(self, query: str, media_type: str, year: int | None = None) -> list[dict]:
        """Return up to 10 TMDB candidates for *query*."""
        try:
            if media_type == "movie":
                results = self.tmdb.search_movie(query, year=year)
            else:
                results = self.tmdb.search_tv(query)
            items = (results.get("results") or [])[:10]
            return [
                {
                    "tmdb_id":      r.get("id"),
                    "title":        r.get("title") or r.get("name") or "",
                    "release_year": _year_from(r.get("release_date") or r.get("first_air_date")),
                    "overview":     r.get("overview") or "",
                    "poster_path":  r.get("poster_path") or "",
                    "vote_average": r.get("vote_average") or 0.0,
                }
                for r in items
            ]
        except Exception as exc:
            log.error("TMDB re-search failed: %s", exc)
            return []

    # ── Save ──────────────────────────────────────────────────────────

    def save_manual_override(self, entity_id: int, fields: dict) -> None:
        """Persist *fields* onto an existing entity and mark it verified."""
        now = datetime.now().isoformat(timespec="seconds")
        allowed = {
            "title", "release_year", "plot", "rating",
            "genres_json", "poster_path", "tmdb_id",
        }
        clean = {k: v for k, v in fields.items() if k in allowed}
        if not clean:
            return
        set_clause = ", ".join(f"{k} = ?" for k in clean)
        values = list(clean.values()) + [now, 1, entity_id]
        with get_connection() as conn:
            conn.execute(
                f"UPDATE media_entities SET {set_clause}, updated_at = ?, manually_verified = ? WHERE id = ?",
                values,
            )
        log.info("Manual override saved for entity_id=%d", entity_id)

    def apply_tmdb_pick(self, entity_id: int, tmdb_id: int, media_type: str) -> None:
        """Fetch full details for *tmdb_id* and overwrite the entity row."""
        try:
            if media_type == "movie":
                details = self.tmdb.get_movie_details(tmdb_id)
                title = details.get("title") or ""
                date_str = details.get("release_date") or ""
            else:
                details = self.tmdb.get_tv_details(tmdb_id)
                title = details.get("name") or ""
                date_str = details.get("first_air_date") or ""

            year = _year_from(date_str)
            genres_json = json.dumps([g["name"] for g in (details.get("genres") or [])])

            self.save_manual_override(entity_id, {
                "tmdb_id":      tmdb_id,
                "title":        title,
                "release_year": year,
                "plot":         details.get("overview") or "",
                "rating":       details.get("vote_average") or 0.0,
                "genres_json":  genres_json,
                "poster_path":  details.get("poster_path") or "",
            })
        except Exception as exc:
            log.error("apply_tmdb_pick failed for tmdb_id=%d: %s", tmdb_id, exc)
            raise


def _year_from(date_str: str | None) -> int | None:
    if date_str and len(date_str) >= 4:
        try:
            return int(date_str[:4])
        except ValueError:
            pass
    return None
