import json
from datetime import datetime, timedelta
from mlm.db.connection import get_connection

class CacheRepository:
    def get_json(self, provider: str, cache_key: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT response_json, expires_at
                FROM api_cache
                WHERE provider = ? AND cache_key = ?
                """,
                (provider, cache_key),
            ).fetchone()

        if not row:
            return None

        expires_at = row["expires_at"]
        if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
            return None

        return json.loads(row["response_json"])

    def set_json(self, provider: str, cache_key: str, payload: dict, ttl_hours: int = 168) -> None:
        expires_at = (datetime.now() + timedelta(hours=ttl_hours)).isoformat(timespec="seconds")
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO api_cache (provider, cache_key, response_json, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    response_json=excluded.response_json,
                    expires_at=excluded.expires_at,
                    fetched_at=CURRENT_TIMESTAMP
                """,
                (provider, cache_key, json.dumps(payload), expires_at),
            )