"""Canned SQL queries used by the Reports view."""
import logging
from mlm.db.connection import get_connection

log = logging.getLogger(__name__)


def top_largest_files(limit: int = 50) -> list[dict]:
    """Return the *limit* largest media files by size."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT mf.file_name, mf.file_path, mf.file_size_bytes,
                   mf.resolution, mf.video_codec, me.title, me.media_type
            FROM media_files mf
            LEFT JOIN media_entities me ON me.id = mf.entity_id
            WHERE mf.removed_at IS NULL
            ORDER BY mf.file_size_bytes DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def files_without_metadata(limit: int = 200) -> list[dict]:
    """Return files that have no linked media entity."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, file_name, file_path, discovered_at
            FROM media_files
            WHERE entity_id IS NULL AND removed_at IS NULL
            ORDER BY discovered_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def scan_history(limit: int = 30) -> list[dict]:
    """Return the most recent scan run records."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT sr.id, d.path AS directory_path,
                   sr.started_at, sr.finished_at, sr.status,
                   sr.files_seen, sr.files_added, sr.files_removed,
                   sr.error_message
            FROM scan_runs sr
            JOIN directories d ON d.id = sr.directory_id
            ORDER BY sr.started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def health_summary() -> dict:
    """Return counts per health_status value."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT health_status, COUNT(*) AS count
            FROM media_files
            WHERE removed_at IS NULL
            GROUP BY health_status
            """
        ).fetchall()
    return {r["health_status"]: r["count"] for r in rows}


def genre_breakdown(limit: int = 20) -> list[dict]:
    """Return the most common genres across all matched media entities.

    Genres are stored as a JSON array; this query uses json_each to
    unnest them and count occurrences.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT json_extract(g.value, '$.name') AS genre,
                   COUNT(*) AS count
            FROM media_entities me,
                 json_each(me.genres_json) AS g
            WHERE me.genres_json IS NOT NULL
              AND me.genres_json != '[]'
            GROUP BY genre
            ORDER BY count DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
