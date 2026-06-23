"""E-4 Folder Restructuring / Auto-Move Service.

Builds a target path for a media file based on a configurable template
and moves the file on disk, updating the DB and writing an action_ledger
entry for full undo support.

Template tokens
---------------
  {media_type}     'movie' | 'show'
  {title}          entity title (sanitised for filesystem)
  {sort_title}     sort-safe title (The Dark Knight -> Dark Knight, The)
  {year}           release year or ''
  {genre}          first genre or 'Unknown'
  {resolution}     '4K' | '1080p' | '720p' | 'SD'
  {video_codec}    e.g. 'HEVC' | 'AVC'
  {first_letter}   first letter of sort_title, uppercase

Default templates
-----------------
  movies: {media_type}/{first_letter}/{title} ({year})
  shows:  {media_type}/{title}/Season {season}

All moves are DRY-RUN by default; pass dry_run=False to execute.
"""
from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

from mlm.db.connection import get_connection

log = logging.getLogger(__name__)

_SANITISE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MULTI_SP = re.compile(r" {2,}")

DEFAULT_MOVIE_TEMPLATE = "{media_type}/{first_letter}/{title} ({year})"
DEFAULT_SHOW_TEMPLATE  = "{media_type}/{title}/Season {season:02d}"


def _sanitise(name: str) -> str:
    """Remove characters illegal on Windows/macOS/Linux filesystems."""
    return _MULTI_SP.sub(" ", _SANITISE.sub("_", name)).strip(" .")


def _resolution_label(width: int | None) -> str:
    if not width:
        return "SD"
    if width >= 3840:
        return "4K"
    if width >= 1920:
        return "1080p"
    if width >= 1280:
        return "720p"
    return "SD"


class FolderRestructureService:
    """Computes and (optionally) executes file moves."""

    def __init__(
        self,
        base_dir: str | Path,
        movie_template: str = DEFAULT_MOVIE_TEMPLATE,
        show_template: str  = DEFAULT_SHOW_TEMPLATE,
    ) -> None:
        self.base_dir        = Path(base_dir)
        self.movie_template  = movie_template
        self.show_template   = show_template

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def preview(self, media_file_id: int) -> dict:
        """Return {'current': str, 'proposed': str, 'will_move': bool}."""
        row = self._load(media_file_id)
        if not row:
            return {"error": "file not found"}
        proposed = self._build_target(row)
        current  = Path(row["file_path"])
        return {
            "current":   str(current),
            "proposed":  str(proposed),
            "will_move": current.resolve() != proposed.resolve(),
        }

    def move_file(
        self,
        media_file_id: int,
        dry_run: bool = True,
    ) -> dict:
        """Move a single file. Returns a result dict."""
        row      = self._load(media_file_id)
        if not row:
            return {"status": "error", "reason": "file not found"}
        src      = Path(row["file_path"])
        dst      = self._build_target(row)

        if src.resolve() == dst.resolve():
            return {"status": "skipped", "reason": "already in correct location"}

        log.info("[Restructure] %s  %s -> %s", "DRY" if dry_run else "MOVE", src, dst)

        if dry_run:
            return {"status": "dry_run", "src": str(src), "dst": str(dst)}

        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            return {
                "status": "error",
                "reason": f"Destination already exists: {dst}",
            }

        try:
            shutil.move(str(src), str(dst))
        except OSError as exc:
            self._ledger(media_file_id, str(src), str(dst), "error", str(exc))
            return {"status": "error", "reason": str(exc)}

        self._update_db(media_file_id, str(src), str(dst))
        self._ledger(media_file_id, str(src), str(dst), "ok", None)
        return {"status": "moved", "src": str(src), "dst": str(dst)}

    def bulk_move(
        self,
        directory_id: int | None = None,
        dry_run: bool = True,
    ) -> list[dict]:
        """Preview or execute moves for all (or a directory's) files."""
        with get_connection() as conn:
            if directory_id is not None:
                rows = conn.execute(
                    "SELECT id FROM media_files "
                    "WHERE removed_at IS NULL AND directory_id=?",
                    (directory_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id FROM media_files WHERE removed_at IS NULL"
                ).fetchall()
        results = []
        for r in rows:
            results.append(self.move_file(r["id"], dry_run=dry_run))
        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load(self, media_file_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT f.*, e.title, e.sort_title, e.release_year,
                       e.genres_json, e.media_type,
                       ep.season_number
                FROM   media_files f
                LEFT JOIN media_entities e  ON e.id = f.entity_id
                LEFT JOIN episodes ep       ON ep.media_file_id = f.id
                WHERE  f.id = ?
                """,
                (media_file_id,),
            ).fetchone()
        return dict(row) if row else None

    def _build_target(self, row: dict) -> Path:
        import json
        title      = _sanitise(row.get("title") or row["file_name"])
        sort_title = _sanitise(row.get("sort_title") or title)
        year       = str(row.get("release_year") or "")
        first      = (sort_title[0].upper() if sort_title else "#")
        media_type = row.get("media_type") or "movie"
        season     = row.get("season_number") or 1
        genres     = []
        try:
            genres = json.loads(row.get("genres_json") or "[]")
        except Exception:  # noqa: BLE001
            pass
        genre      = genres[0].get("name", "Unknown") if genres else "Unknown"
        resolution = _resolution_label(row.get("width"))
        codec      = (row.get("video_codec") or "Unknown").upper()
        ext        = Path(row["file_path"]).suffix

        tmpl = self.show_template if media_type in ("show", "episode") else self.movie_template
        rel  = tmpl.format(
            media_type=media_type,
            title=title,
            sort_title=sort_title,
            year=year,
            genre=genre,
            resolution=resolution,
            video_codec=codec,
            first_letter=first,
            season=season,
        )
        return self.base_dir / rel / (title + ext)

    def _update_db(self, fid: int, old: str, new: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE media_files SET file_path=?, moved_to_path=? WHERE id=?",
                (new, old, fid),
            )

    def _ledger(self, fid: int, old: str, new: str, status: str, err: str | None) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO action_ledger
                    (action_type, media_file_id, old_path, new_path, status, error_message)
                VALUES ('auto_move', ?, ?, ?, ?, ?)
                """,
                (fid, old, new, status, err),
            )
