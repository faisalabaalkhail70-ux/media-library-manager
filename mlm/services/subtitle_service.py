"""H-2 Subtitle File Tracking.

Scans for subtitle sidecars alongside media files and maintains the
subtitle_files table. Supports SRT, ASS, SSA, VTT, and SUB formats.

Language detection is done by matching common ISO-639 2-letter codes
or full language names in the filename stem
(e.g. movie.en.srt, movie.french.srt, movie.forced.en.srt).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from mlm.db.connection import get_connection

log = logging.getLogger(__name__)

_SUB_EXTS: frozenset[str] = frozenset({".srt", ".ass", ".ssa", ".vtt", ".sub"})

# ISO-639-1 / common language name map
_LANG_PATTERNS: dict[str, str] = {
    r"\ben\b|english":         "en",
    r"\bar\b|arabic":          "ar",
    r"\bfr\b|french|francais": "fr",
    r"\bde\b|german|deutsch":  "de",
    r"\bes\b|spanish|espanol": "es",
    r"\bja\b|japanese":        "ja",
    r"\bzh\b|chinese":         "zh",
    r"\bko\b|korean":          "ko",
    r"\bpt\b|portuguese":      "pt",
    r"\bit\b|italian":         "it",
    r"\bru\b|russian":         "ru",
    r"\bnl\b|dutch":           "nl",
    r"\btr\b|turkish":         "tr",
}


def _detect_language(stem: str) -> str | None:
    s = stem.lower()
    for pattern, code in _LANG_PATTERNS.items():
        if re.search(pattern, s):
            return code
    return None


def _is_forced(stem: str) -> bool:
    return bool(re.search(r"\bforced\b", stem, re.IGNORECASE))


def _is_sdh(stem: str) -> bool:
    return bool(re.search(r"\b(sdh|hi|hearing.impaired)\b", stem, re.IGNORECASE))


class SubtitleService:
    """Discovers and tracks subtitle sidecar files."""

    def scan_for_media_file(self, media_file_id: int) -> list[dict]:
        """Find subtitle sidecars next to the media file and upsert DB records."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT file_path FROM media_files WHERE id=?", (media_file_id,)
            ).fetchone()
        if not row:
            return []

        media_path = Path(row["file_path"])
        found: list[dict] = []

        for ext in _SUB_EXTS:
            # Scan same directory for files sharing the same stem prefix
            for sub_path in media_path.parent.glob(f"{media_path.stem}*{ext}"):
                result = self._upsert_subtitle(media_file_id, sub_path)
                found.append(result)

        log.info(
            "[Subtitles] Found %d subtitle(s) for file_id=%d", len(found), media_file_id
        )
        return found

    def scan_directory(self, directory_id: int) -> int:
        """Scan an entire directory for subtitle files. Returns count upserted."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT path FROM directories WHERE id=?", (directory_id,)
            ).fetchone()
            if not row:
                return 0
            media_rows = conn.execute(
                "SELECT id, file_path FROM media_files "
                "WHERE directory_id=? AND removed_at IS NULL",
                (directory_id,),
            ).fetchall()

        total = 0
        for mrow in media_rows:
            total += len(self.scan_for_media_file(mrow["id"]))
        return total

    def get_subtitles(self, media_file_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM subtitle_files WHERE media_file_id=? AND removed_at IS NULL",
                (media_file_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_removed(self, subtitle_id: int) -> None:
        from datetime import datetime
        with get_connection() as conn:
            conn.execute(
                "UPDATE subtitle_files SET removed_at=? WHERE id=?",
                (datetime.utcnow().isoformat(), subtitle_id),
            )

    # ------------------------------------------------------------------

    def _upsert_subtitle(self, media_file_id: int, path: Path) -> dict:
        stem     = path.stem
        lang     = _detect_language(stem)
        forced   = _is_forced(stem)
        sdh      = _is_sdh(stem)
        fmt      = path.suffix.lstrip(".")
        size     = path.stat().st_size if path.exists() else None

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO subtitle_files
                    (media_file_id, file_path, language, format,
                     is_forced, is_sdh, file_size_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    language        = excluded.language,
                    format          = excluded.format,
                    is_forced       = excluded.is_forced,
                    is_sdh          = excluded.is_sdh,
                    file_size_bytes = excluded.file_size_bytes,
                    removed_at      = NULL
                """,
                (media_file_id, str(path), lang, fmt, int(forced), int(sdh), size),
            )
        return {
            "file_path": str(path),
            "language":  lang,
            "format":    fmt,
            "is_forced": forced,
            "is_sdh":    sdh,
        }
