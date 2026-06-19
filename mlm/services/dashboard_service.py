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
                "storage_gb": 0.0,
                "watch_hours": 0.0,
            }

        total_files = int(len(df))
        total_movies = int((df["media_type"] == "movie").sum()) if "media_type" in df else 0
        total_shows = int((df["media_type"] == "show").sum()) if "media_type" in df else 0
        total_episodes = int((df["media_type"] == "show").sum()) if "media_type" in df else 0
        storage_gb = float(df["file_size_bytes"].fillna(0).sum() / (1024 ** 3))
        watch_hours = float(df["duration_seconds"].fillna(0).sum() / 3600)

        return {
            "total_files": total_files,
            "total_movies": total_movies,
            "total_shows": total_shows,
            "total_episodes": total_episodes,
            "storage_gb": round(storage_gb, 2),
            "watch_hours": round(watch_hours, 2),
        }

    def resolution_breakdown(self) -> list[dict]:
        df = pd.read_sql_query(
            """
            SELECT resolution, COUNT(*) AS count
            FROM media_files
            WHERE removed_at IS NULL
            GROUP BY resolution
            ORDER BY count DESC
            """,
            self.conn,
        )
        return df.fillna("Unknown").to_dict(orient="records")

    def codec_breakdown(self) -> list[dict]:
        df = pd.read_sql_query(
            """
            SELECT video_codec, COUNT(*) AS count
            FROM media_files
            WHERE removed_at IS NULL
            GROUP BY video_codec
            ORDER BY count DESC
            """,
            self.conn,
        )
        return df.fillna("Unknown").to_dict(orient="records")

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