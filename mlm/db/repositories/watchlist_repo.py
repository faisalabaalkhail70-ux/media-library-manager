"""Repository for the watchlist table."""
from mlm.db.connection import get_connection


class WatchlistRepository:

    def list_items(self, watched: bool | None = None) -> list[dict]:
        """Return watchlist entries.  watched=None → all, True → seen, False → pending."""
        clause = ""
        if watched is True:
            clause = "AND w.watched_at IS NOT NULL"
        elif watched is False:
            clause = "AND w.watched_at IS NULL"

        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT w.id, w.entity_id, w.priority, w.notes,
                       w.added_at, w.watched_at,
                       me.title, me.media_type, me.release_year,
                       me.rating, me.genres_json
                FROM watchlist w
                JOIN media_entities me ON me.id = w.entity_id
                {clause}
                ORDER BY w.priority ASC, me.title COLLATE NOCASE
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def add(self, entity_id: int, priority: int = 5, notes: str = "") -> None:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist(entity_id, priority, notes) VALUES (?, ?, ?)",
                (entity_id, priority, notes),
            )

    def remove(self, watchlist_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM watchlist WHERE id = ?", (watchlist_id,))

    def mark_watched(self, watchlist_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE watchlist SET watched_at = CURRENT_TIMESTAMP WHERE id = ?",
                (watchlist_id,),
            )

    def mark_unwatched(self, watchlist_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE watchlist SET watched_at = NULL WHERE id = ?",
                (watchlist_id,),
            )

    def set_priority(self, watchlist_id: int, priority: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE watchlist SET priority = ? WHERE id = ?",
                (max(1, min(10, priority)), watchlist_id),
            )

    def update_notes(self, watchlist_id: int, notes: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE watchlist SET notes = ? WHERE id = ?",
                (notes, watchlist_id),
            )

    def search_entities(self, query: str) -> list[dict]:
        like = f"%{query}%"
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT me.id AS entity_id, me.title, me.media_type, me.release_year
                FROM media_entities me
                WHERE me.title LIKE ?
                  AND me.id NOT IN (SELECT entity_id FROM watchlist)
                ORDER BY me.title COLLATE NOCASE
                LIMIT 50
                """,
                (like,),
            ).fetchall()
        return [dict(r) for r in rows]

    def is_on_watchlist(self, entity_id: int) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM watchlist WHERE entity_id = ?", (entity_id,)
            ).fetchone()
        return row is not None
