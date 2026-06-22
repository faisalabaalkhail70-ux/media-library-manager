"""Repository for the collections and collection_items tables."""
from mlm.db.connection import get_connection


class CollectionsRepository:

    # ── Collections CRUD ─────────────────────────────────────────

    def list_collections(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.name, c.description, c.created_at,
                       COUNT(ci.id) AS item_count
                FROM collections c
                LEFT JOIN collection_items ci ON ci.collection_id = c.id
                GROUP BY c.id
                ORDER BY c.name COLLATE NOCASE
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def create_collection(self, name: str, description: str = "") -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO collections(name, description) VALUES (?, ?)",
                (name.strip(), description.strip()),
            )
            return cur.lastrowid

    def rename_collection(self, collection_id: int, new_name: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE collections SET name = ? WHERE id = ?",
                (new_name.strip(), collection_id),
            )

    def delete_collection(self, collection_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))

    # ── Items ─────────────────────────────────────────────────────

    def get_items(self, collection_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT me.id AS entity_id, me.title, me.media_type,
                       me.release_year, me.rating, me.genres_json,
                       ci.added_at
                FROM collection_items ci
                JOIN media_entities me ON me.id = ci.entity_id
                WHERE ci.collection_id = ?
                ORDER BY me.title COLLATE NOCASE
                """,
                (collection_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_item(self, collection_id: int, entity_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO collection_items(collection_id, entity_id) VALUES (?, ?)",
                (collection_id, entity_id),
            )

    def remove_item(self, collection_id: int, entity_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM collection_items WHERE collection_id = ? AND entity_id = ?",
                (collection_id, entity_id),
            )

    def entity_collections(self, entity_id: int) -> list[int]:
        """Return the collection IDs that contain a given entity."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT collection_id FROM collection_items WHERE entity_id = ?",
                (entity_id,),
            ).fetchall()
        return [r["collection_id"] for r in rows]

    def search_entities(self, query: str) -> list[dict]:
        """Search media_entities by title for the Add-to-Collection dialog."""
        like = f"%{query}%"
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id AS entity_id, title, media_type, release_year
                FROM media_entities
                WHERE title LIKE ?
                ORDER BY title COLLATE NOCASE
                LIMIT 50
                """,
                (like,),
            ).fetchall()
        return [dict(r) for r in rows]
