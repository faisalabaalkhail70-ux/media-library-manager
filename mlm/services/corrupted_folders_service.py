"""Service: aggregate corrupted files (health_status='error') by parent folder.

Returns a list of dicts, one per affected folder, sorted by corrupted_count DESC:

    [
        {
            'title':           'Breaking Bad',   # media_entities.title (or filename stem)
            'media_type':      'show',            # 'movie' | 'show' | None
            'folder_path':     r'D:\Media\TV Shows\Breaking Bad',
            'corrupted_count': 10,
        },
        ...
    ]

If a file has no linked entity the folder name is used as the title.
"""
from __future__ import annotations
import os
from mlm.db.connection import get_connection


class CorruptedFoldersService:
    """Read-only service — no writes."""

    def corrupted_folders(self) -> list[dict]:
        """Return one row per parent_folder that contains ≥1 error-status file."""
        sql = """
            SELECT
                mf.parent_folder                          AS folder_path,
                me.title                                  AS entity_title,
                me.media_type                             AS media_type,
                COUNT(mf.id)                              AS corrupted_count
            FROM   media_files AS mf
            LEFT JOIN media_entities AS me ON me.id = mf.entity_id
            WHERE  mf.removed_at  IS NULL
              AND  mf.health_status = 'error'
            GROUP BY mf.parent_folder
            ORDER BY corrupted_count DESC, folder_path
        """
        with get_connection() as conn:
            rows = conn.execute(sql).fetchall()

        result = []
        for row in rows:
            folder = row["folder_path"] or ""
            title  = row["entity_title"]
            if not title:
                # Fall back to the last path component
                title = os.path.basename(folder.rstrip("\\/")) or folder
            result.append({
                "title":           title,
                "media_type":      row["media_type"],
                "folder_path":     folder,
                "corrupted_count": row["corrupted_count"],
            })
        return result

    def total_corrupted_files(self) -> int:
        """Quick scalar: total error-status files (for badge counts)."""
        sql = """
            SELECT COUNT(*) AS n
            FROM   media_files
            WHERE  removed_at IS NULL
              AND  health_status = 'error'
        """
        with get_connection() as conn:
            row = conn.execute(sql).fetchone()
        return row["n"] if row else 0
