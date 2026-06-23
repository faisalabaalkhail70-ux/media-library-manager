import pandas as pd
from mlm.db.connection import get_connection


class DashboardService:

    def library_overview(self) -> dict:
        """Return a single-pass library stats dict.

        Previously opened two separate ``get_connection()`` contexts for one
        logical read, which introduced a consistency window between them and
        doubled the connection overhead.  Both queries now run inside a single
        connection.
        """
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
            # Fetch show count in the same connection/transaction.
            total_shows = conn.execute(
                "SELECT COUNT(*) FROM media_entities WHERE media_type = 'show'"
            ).fetchone()[0]

        if df.empty:
            return {
                "total_files": 0, "total_movies": 0, "total_shows": 0,
                "total_episodes": 0, "unmatched": 0,
                "storage_gb": 0.0, "watch_hours": 0.0,
            }

        total_files    = int(len(df))
        total_movies   = int((df["media_type"] == "movie").sum())
        total_episodes = int((df["media_type"] == "show").sum())
        unmatched      = int(df["media_type"].isna().sum())
        storage_gb     = float(df["file_size_bytes"].fillna(0).sum() / (1024 ** 3))
        watch_hours    = float(df["duration_seconds"].fillna(0).sum() / 3600)

        return {
            "total_files": total_files, "total_movies": total_movies,
            "total_shows": int(total_shows), "total_episodes": total_episodes,
            "unmatched": unmatched,
            "storage_gb": round(storage_gb, 2),
            "watch_hours": round(watch_hours, 2),
        }

    def shows_completion(self) -> dict:
        """Return counts of Complete / Partial / Not Started shows.

        A show is:
          - Complete   : 0 missing episodes
          - Partial    : some missing, some present
          - Not Started: ALL episodes missing (or no episode rows at all)
        """
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

    def health_breakdown(self) -> list[dict]:
        with get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT COALESCE(health_status, 'unknown') AS health_status,
                       COUNT(*) AS count
                FROM media_files WHERE removed_at IS NULL
                GROUP BY health_status ORDER BY count DESC
                """,
                conn,
            )
        return df.to_dict(orient="records")

    def recent_additions(self, limit: int = 10) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT mf.file_name, mf.file_path, mf.scanned_at,
                       me.title AS matched_title, me.media_type
                FROM media_files mf
                LEFT JOIN media_entities me ON me.id = mf.entity_id
                WHERE mf.removed_at IS NULL
                ORDER BY mf.scanned_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
