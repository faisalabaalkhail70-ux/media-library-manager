import pandas as pd
from mlm.db.connection import create_connection


class DashboardService:
    def __init__(self) -> None:
        self.conn = create_connection()

    def library_overview(self) -> dict:
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
            self.conn,
        )

        if df.empty:
            return {
                "total_files": 0,
                "total_movies": 0,
                "total_shows": 0,
                "total_episodes": 0,
                "unmatched": 0,
                "storage_gb": 0.0,
                "watch_hours": 0.0,
            }

        total_files    = int(len(df))
        total_movies   = int((df["media_type"] == "movie").sum())
        total_episodes = int((df["media_type"] == "show").sum())
        unmatched      = int(df["media_type"].isna().sum())
        storage_gb     = float(df["file_size_bytes"].fillna(0).sum() / (1024 ** 3))
        watch_hours    = float(df["duration_seconds"].fillna(0).sum() / 3600)

        # total_shows = distinct entities of type show
        shows_df = pd.read_sql_query(
            "SELECT COUNT(*) AS c FROM media_entities WHERE media_type = 'show'",
            self.conn,
        )
        total_shows = int(shows_df["c"].iloc[0])

        return {
            "total_files":    total_files,
            "total_movies":   total_movies,
            "total_shows":    total_shows,
            "total_episodes": total_episodes,
            "unmatched":      unmatched,
            "storage_gb":     round(storage_gb, 2),
            "watch_hours":    round(watch_hours, 2),
        }

    def resolution_breakdown(self) -> list[dict]:
        df = pd.read_sql_query(
            """
            SELECT COALESCE(resolution, 'Unknown') AS resolution,
                   COUNT(*) AS count
            FROM media_files
            WHERE removed_at IS NULL
            GROUP BY resolution
            ORDER BY count DESC
            """,
            self.conn,
        )
        return df.to_dict(orient="records")

    def codec_breakdown(self) -> list[dict]:
        df = pd.read_sql_query(
            """
            SELECT COALESCE(video_codec, 'Unknown') AS video_codec,
                   COUNT(*) AS count
            FROM media_files
            WHERE removed_at IS NULL
            GROUP BY video_codec
            ORDER BY count DESC
            """,
            self.conn,
        )
        return df.to_dict(orient="records")

    def recent_additions(self, limit: int = 20) -> list[dict]:
        df = pd.read_sql_query(
            """
            SELECT file_name, file_path, discovered_at
            FROM media_files
            WHERE removed_at IS NULL
            ORDER BY discovered_at DESC
            LIMIT ?
            """,
            self.conn,
            params=(limit,),
        )
        return df.to_dict(orient="records")

    def missing_episodes_count(self) -> int:
        df = pd.read_sql_query(
            "SELECT COUNT(*) AS c FROM episodes WHERE is_missing = 1",
            self.conn,
        )
        return int(df["c"].iloc[0])