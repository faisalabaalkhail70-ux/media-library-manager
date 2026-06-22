"""Build rename previews and apply bulk renames with ledger tracking."""
import logging
import os
import re

from mlm.db.connection import get_connection
from mlm.db.repositories.actions_repo import ActionsRepository
from mlm.utils.filesystem import move_file, safe_exists

log = logging.getLogger(__name__)

INVALID_CHARS = r'\/:*?"<>|'


def sanitize_filename(name: str) -> str:
    """Strip filesystem-illegal characters from *name*."""
    return "".join(c for c in name if c not in INVALID_CHARS).strip()


class RenameService:
    """Preview and apply bulk file renames tracked in the action ledger."""

    def __init__(self, actions_repo: ActionsRepository | None = None) -> None:
        self.actions_repo = actions_repo or ActionsRepository()

    def _format_template(self, row: dict, template: str) -> str:
        ext = row.get("extension") or os.path.splitext(row["file_name"])[1]
        values = {
            "{Title}": row.get("title") or row.get("show_title") or row.get("file_name", ""),
            "{Year}": str(row.get("release_year") or ""),
            "{Resolution}": row.get("resolution") or "",
            "{Season:02}": (
                f'{int(row["season_number"]):02d}' if row.get("season_number") is not None else ""
            ),
            "{Episode:02}": (
                f'{int(row["episode_number"]):02d}' if row.get("episode_number") is not None else ""
            ),
            "{Ext}": ext,
        }
        new_name = template
        for token, value in values.items():
            new_name = new_name.replace(token, value)
        new_name = re.sub(r"\s+", " ", new_name).strip()
        return sanitize_filename(new_name)

    def list_renamable_files(self, limit: int = 5000) -> list[dict]:
        """Return files eligible for renaming (not removed)."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    mf.id, mf.file_path, mf.file_name, mf.extension, mf.resolution,
                    me.title, me.release_year,
                    ep.season_number, ep.episode_number
                FROM media_files mf
                LEFT JOIN media_entities me ON me.id = mf.entity_id
                LEFT JOIN episodes ep ON ep.media_file_id = mf.id
                WHERE mf.removed_at IS NULL
                ORDER BY mf.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def build_preview(self, template: str) -> list[dict]:
        """Return a list of rename proposals for *template* without touching the filesystem."""
        previews = []
        for row in self.list_renamable_files():
            old_path = row["file_path"]
            old_name = row["file_name"]
            folder = os.path.dirname(old_path)
            new_name = self._format_template(row, template)
            new_path = os.path.join(folder, new_name)

            if not new_name:
                status = "invalid"
            elif new_name == old_name:
                status = "unchanged"
            elif safe_exists(new_path):
                status = "conflict"
            else:
                status = "valid"

            previews.append({
                "media_file_id": row["id"],
                "old_name": old_name,
                "old_path": old_path,
                "new_name": new_name,
                "new_path": new_path,
                "status": status,
            })
        return previews

    def apply_preview(self, preview_rows: list[dict]) -> dict:
        """Apply all ``'valid'`` rows from a preview batch.

        Returns:
            ``{"success": int, "failed": int}``
        """
        success = failed = 0
        with get_connection() as conn:
            for row in preview_rows:
                if row["status"] != "valid":
                    continue

                action_id = self.actions_repo.create_action(
                    action_type="rename",
                    media_file_id=row["media_file_id"],
                    old_path=row["old_path"],
                    new_path=row["new_path"],
                    status="pending",
                )

                try:
                    move_file(row["old_path"], row["new_path"])
                    conn.execute(
                        """
                        UPDATE media_files
                        SET file_path = ?, file_name = ?, parent_folder = ?
                        WHERE id = ?
                        """,
                        (
                            row["new_path"],
                            os.path.basename(row["new_path"]),
                            os.path.dirname(row["new_path"]),
                            row["media_file_id"],
                        ),
                    )
                    self.actions_repo.mark_done(action_id)
                    success += 1
                    log.info("Renamed: %s → %s", row["old_path"], row["new_path"])
                except Exception as exc:
                    self.actions_repo.mark_failed(action_id, str(exc))
                    failed += 1
                    log.error("Rename failed for %s: %s", row["old_path"], exc, exc_info=True)

        return {"success": success, "failed": failed}
