from mlm.db.connection import get_connection

class SettingsRepository:
    def get(self, key: str, default: str = "") -> str:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?",
                (key,),
            ).fetchone()
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, value),
            )