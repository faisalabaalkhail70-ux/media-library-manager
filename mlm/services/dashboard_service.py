import pandas as pd
from mlm.db.connection import get_connection


def _fmt_storage(bytes_total: float) -> str:
    """Return a human-readable storage string: TB if >= 1 TB, else GB."""
    gb = bytes_total / (1024 ** 3)
    tb = bytes_total / (1024 ** 4)
    if tb >= 1.0:
        return f"{tb:.2f} TB"
    return f"{gb:.1f} GB"


def _fmt_watch_hours(total_seconds: float) -> str:
    """Return a human-readable watch-time string.

    <  60 min  → "N min"
    <  1000 h  → "1,234 h"
    >= 1000 h  → "1.2k h"
    """
    minutes = total_seconds / 60
    hours   = total_seconds / 3600
    if hours < 1.0:
        return f"{int(minutes)} min"
    if hours < 1000:
        return f"{int(hours):,} h"
    return f"{hours / 1000:.1f}k h"


class DashboardService:

    def library_overview(self) -> dict:
        with get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT
                    mf.id,
                    mf.file_size_bytes,
                    mf.duration_seconds,
                    mf.resolution,
                    mf.video_codec,
                    me.media_type
                FROM media_files mf
                LEFT JOIN media_entities me ON me.id = mf.entity_id
                WHERE mf.removed_at IS NULL
                """,
                conn,
            )

        if df.empty:
            return {
                "total_files": 0, "total_movies": 0, "total_shows": 0,
                "total_episodes": 0, "unmatched": 0,
                "storage_gb": 0.0, "storage_display": "0 GB",
                "watch_hours": 0.0, "watch_display": "0 min",
            }

        total_files    = int(len(df))
        total_movies   = int((df["media_type"] == "movie").sum())
        total_episodes = int((df["media_type"] == "show").sum())
        unmatched      = int(df["media_type"].isna().sum())
        total_bytes    = float(df["file_size_bytes"].fillna(0).sum())
        storage_gb     = total_bytes / (1024 ** 3)
        total_seconds  = float(df["duration_seconds"].fillna(0).sum())
        watch_hours    = total_seconds / 3600

        with get_connection() as conn:
            shows_df = pd.read_sql_query(
                "SELECT COUNT(*) AS c FROM media_entities WHERE media_type = 'show'",
                conn,
            )
        total_shows = int(shows_df["c"].iloc[0])

        return {
            "total_files":      total_files,
            "total_movies":     total_movies,
            "total_shows":      total_shows,
            "total_episodes":   total_episodes,
            "unmatched":        unmatched,
            "storage_gb":       round(storage_gb, 2),
            "storage_display":  _fmt_storage(total_bytes),
            "watch_hours":      round(watch_hours, 2),
            "watch_display":    _fmt_watch_hours(total_seconds),
        }

    def shows_completion(self) -> dict:
        """Return counts of Complete / Partial / Not Started shows."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    me.id,
                    COALESCE(SUM(CASE WHEN ep.is_missing = 0 THEN 1 ELSE 0 END), 0) AS have,
                    COALESCE(SUM(CASE WHEN ep.is_missing = 1 THEN 1 ELSE 0 END), 0) AS missing
                FROM media_entities me
                LEFT JOIN episodes ep ON ep.entity_id = me.id
                WHERE me.media_type = 'show'
                GROUP BY me.id
                """
            ).fetchall()

        complete = partial = not_started = 0
        for r in rows:
            have, miss = r["have"], r["missing"]
            if miss == 0 and have > 0:
                complete += 1
            elif have == 0:
                not_started += 1
            else:
                partial += 1
        return {"complete": complete, "partial": partial, "not_started": not_started}

    def resolution_breakdown(self) -> list[dict]:
        with get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT COALESCE(resolution, 'Unknown') AS resolution,
                       COUNT(*) AS count
                FROM media_files WHERE removed_at IS NULL
                GROUP BY resolution ORDER BY count DESC
                """,
                conn,
            )
        return df.to_dict(orient="records")

    def codec_breakdown(self) -> list[dict]:
        with get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT COALESCE(video_codec, 'Unknown') AS video_codec,
                       COUNT(*) AS count
                FROM media_files WHERE removed_at IS NULL
                GROUP BY video_codec ORDER BY count DESC
                """,
                conn,
            )
        return df.to_dict(orient="records")

    def recent_additions(self, limit: int = 20) -> list[dict]:
        with get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT file_name, file_path, discovered_at
                FROM media_files WHERE removed_at IS NULL
                ORDER BY discovered_at DESC LIMIT ?
                """,
                conn,
                params=(limit,),
            )
        return df.to_dict(orient="records")

    def missing_episodes_count(self) -> int:
        with get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT COUNT(*) AS c FROM episodes WHERE is_missing = 1",
                conn,
            )
        return int(df["c"].iloc[0])
