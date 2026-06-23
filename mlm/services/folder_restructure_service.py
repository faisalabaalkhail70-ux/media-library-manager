"""E-4 — Folder Restructuring / Auto-Move service.

Builds a canonical target path from a configurable template and moves
files there.  Every move is logged in the ``restructure_log`` table.

Template tokens
---------------
{media_type}   movie | show
{title}        Sanitised title from the DB entity
{year}         Release year (or empty string)
{resolution}   e.g. 1080p, 4K (derived from ffprobe metadata if available)
{codec}        e.g. H.264, H.265
{extension}    e.g. .mkv

Default template:  ``{media_type}/{title} ({year})/"""
from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from mlm.db.connection import get_connection
from mlm.db.repositories.settings_repo import SettingsRepository

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_DEFAULT_TEMPLATE = "{media_type}/{title} ({year})"


def _sanitise(name: str) -> str:
    """Replace characters illegal in filesystem names."""
    return _UNSAFE_CHARS.sub("_", name).strip(". ")


class FolderRestructureService:
    """Move media files into a canonical directory hierarchy."""

    def __init__(self) -> None:
        self._settings = SettingsRepository()

    @property
    def template(self) -> str:
        return self._settings.get("folder_template", _DEFAULT_TEMPLATE)

    def preview(self, directory_id: int) -> list[dict]:
        """Return a list of proposed moves without touching disk."""
        return self._collect_moves(directory_id, dry_run=True)

    def restructure_directory(
        self,
        directory_id: int,
        dry_run: bool = False,
    ) -> list[dict]:
        """Move files and return a log of every action taken."""
        results = self._collect_moves(directory_id, dry_run=dry_run)
        if not dry_run:
            self._persist_log(results)
        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _collect_moves(
        self,
        directory_id: int,
        dry_run: bool,
    ) -> list[dict]:
        with get_connection() as conn:
            dir_row = conn.execute(
                "SELECT path FROM directories WHERE id = ?", (directory_id,)
            ).fetchone()
            if not dir_row:
                raise ValueError(f"Directory {directory_id} not found")
            root = Path(dir_row["path"])

            rows = conn.execute(
                """
                SELECT
                    mf.id, mf.file_path, mf.file_name,
                    e.title, e.release_year, e.media_type,
                    mf.metadata_json
                FROM media_files mf
                LEFT JOIN file_entity_links fel ON fel.file_id = mf.id
                LEFT JOIN media_entities e ON e.id = fel.entity_id
                WHERE mf.directory_id = ?
                  AND mf.is_missing = 0
                """,
                (directory_id,),
            ).fetchall()

        results: list[dict] = []
        for row in rows:
            current = Path(row["file_path"])
            if not current.exists():
                continue
            target = self._build_target_path(row, root)
            if target == current:
                continue
            entry = {
                "file_id":  row["id"],
                "old_path": str(current),
                "new_path": str(target),
                "status":   "pending",
            }
            if not dry_run:
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(current), str(target))
                    entry["status"] = "moved"
                    # Update DB immediately so health scans stay accurate
                    with get_connection() as conn:
                        conn.execute(
                            "UPDATE media_files SET file_path=? WHERE id=?",
                            (str(target), row["id"]),
                        )
                    log.info("Moved: %s → %s", current, target)
                except OSError as exc:
                    entry["status"] = f"error: {exc}"
                    log.error("Move failed %s: %s", current, exc)
            results.append(entry)
        return results

    def _build_target_path(self, row: dict, root: Path) -> Path:
        import json
        meta: dict = {}
        if row["metadata_json"]:
            try:
                meta = json.loads(row["metadata_json"])
            except Exception:  # noqa: BLE001
                pass

        resolution = self._extract_resolution(meta)
        codec = self._extract_codec(meta)
        ext = Path(row["file_name"]).suffix

        tokens = {
            "media_type": _sanitise(row["media_type"] or "unknown"),
            "title":      _sanitise(row["title"] or Path(row["file_name"]).stem),
            "year":       str(row["release_year"]) if row["release_year"] else "",
            "resolution": resolution,
            "codec":      codec,
            "extension":  ext,
        }
        rel_dir = self.template.format_map(tokens)
        filename = _sanitise(Path(row["file_name"]).stem) + ext
        return root / rel_dir / filename

    @staticmethod
    def _extract_resolution(meta: dict) -> str:
        streams = meta.get("streams", [])
        for s in streams:
            if s.get("codec_type") == "video":
                h = s.get("height", 0)
                if h >= 2160:
                    return "4K"
                if h >= 1080:
                    return "1080p"
                if h >= 720:
                    return "720p"
                return f"{h}p" if h else ""
        return ""

    @staticmethod
    def _extract_codec(meta: dict) -> str:
        streams = meta.get("streams", [])
        for s in streams:
            if s.get("codec_type") == "video":
                return s.get("codec_name", "").upper()
        return ""

    def _persist_log(self, entries: list[dict]) -> None:
        rows = [
            (e["file_id"], e["old_path"], e["new_path"], e["status"])
            for e in entries
        ]
        with get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO restructure_log (file_id, old_path, new_path, status, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                rows,
            )
