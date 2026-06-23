"""R-4 Per-File Notes & Tags.

Provides CRUD operations for the file_notes table.  Tags are stored as
a comma-separated string and exposed as a Python list for convenience.

Tag rules
---------
  - Lowercase, ASCII letters/digits/hyphens only
  - Max 32 characters per tag
  - Max 20 tags per file
  - Empty tag strings are ignored
"""
from __future__ import annotations

import logging
import re
from datetime import datetime

from mlm.db.connection import get_connection

log = logging.getLogger(__name__)

_TAG_RE  = re.compile(r"^[a-z0-9][a-z0-9\-]{0,31}$")
_MAX_TAGS = 20


def _normalise_tags(raw: list[str]) -> list[str]:
    """Deduplicate, lowercase, validate, and cap the tag list."""
    seen: list[str] = []
    for t in raw:
        t = t.strip().lower()
        if not t:
            continue
        if not _TAG_RE.match(t):
            log.warning("[Notes] Ignoring invalid tag: '%s'", t)
            continue
        if t not in seen:
            seen.append(t)
    return seen[:_MAX_TAGS]


class NotesService:
    """CRUD service for per-file notes and tags."""

    def get(self, media_file_id: int) -> dict:
        """Return {'note': str, 'tags': list[str]} for a file."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT note, tags FROM file_notes WHERE media_file_id=?",
                (media_file_id,),
            ).fetchone()
        if not row:
            return {"note": "", "tags": []}
        tags = [t for t in (row["tags"] or "").split(",") if t]
        return {"note": row["note"] or "", "tags": tags}

    def save(
        self,
        media_file_id: int,
        note: str = "",
        tags: list[str] | None = None,
    ) -> dict:
        """Create or replace the note/tags for a file."""
        clean_tags = _normalise_tags(tags or [])
        tags_str   = ",".join(clean_tags)
        now        = datetime.utcnow().isoformat()
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO file_notes (media_file_id, note, tags, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(media_file_id) DO UPDATE SET
                    note       = excluded.note,
                    tags       = excluded.tags,
                    updated_at = excluded.updated_at
                """,
                (media_file_id, note.strip(), tags_str, now),
            )
        log.debug("[Notes] Saved for file_id=%d: tags=%s", media_file_id, clean_tags)
        return {"note": note.strip(), "tags": clean_tags}

    def add_tag(self, media_file_id: int, tag: str) -> list[str]:
        """Append a single tag (idempotent)."""
        current = self.get(media_file_id)
        tags    = current["tags"]
        tag     = tag.strip().lower()
        if tag not in tags:
            tags.append(tag)
        self.save(media_file_id, note=current["note"], tags=tags)
        return self.get(media_file_id)["tags"]

    def remove_tag(self, media_file_id: int, tag: str) -> list[str]:
        """Remove a single tag."""
        current = self.get(media_file_id)
        tags    = [t for t in current["tags"] if t != tag.strip().lower()]
        self.save(media_file_id, note=current["note"], tags=tags)
        return tags

    def delete(self, media_file_id: int) -> None:
        """Remove note and tags for a file entirely."""
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM file_notes WHERE media_file_id=?", (media_file_id,)
            )

    def search_by_tag(self, tag: str, limit: int = 200) -> list[dict]:
        """Return list of {media_file_id, file_name, note, tags} matching *tag*."""
        tag = tag.strip().lower()
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT fn.media_file_id, mf.file_name, fn.note, fn.tags
                FROM   file_notes fn
                JOIN   media_files mf ON mf.id = fn.media_file_id
                WHERE  (',' || fn.tags || ',') LIKE ('%,' || ? || ',%')
                LIMIT  ?
                """,
                (tag, limit),
            ).fetchall()
        results = []
        for r in rows:
            results.append({
                "media_file_id": r["media_file_id"],
                "file_name":     r["file_name"],
                "note":          r["note"] or "",
                "tags":          [t for t in (r["tags"] or "").split(",") if t],
            })
        return results

    def all_tags(self) -> list[str]:
        """Return sorted list of all distinct tags in use across the library."""
        with get_connection() as conn:
            rows = conn.execute("SELECT tags FROM file_notes WHERE tags != ''").fetchall()
        tag_set: set[str] = set()
        for r in rows:
            for t in (r["tags"] or "").split(","):
                if t:
                    tag_set.add(t)
        return sorted(tag_set)
