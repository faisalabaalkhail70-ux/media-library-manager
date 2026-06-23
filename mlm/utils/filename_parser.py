"""Filename parser — extracts title, year, season, and episode from file names.

Changes in v1.1
---------------
* Replaced os.path.splitext with PurePosixPath.stem for consistency with
  the rest of the codebase which already uses pathlib everywhere (issue #10).
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath

_EP_PATTERN   = re.compile(r"[Ss](\d{1,2})[Ee](\d{1,2})")
_YEAR_PATTERN = re.compile(r"(\d{4})")
_JUNK_CHARS   = re.compile(r"[._\-]+")


def parse_filename(file_name: str) -> dict:
    """Return a dict with keys: title, year, season, episode, media_type."""
    stem = PurePosixPath(file_name).stem

    season: int | None  = None
    episode: int | None = None
    ep_match = _EP_PATTERN.search(stem)
    if ep_match:
        season      = int(ep_match.group(1))
        episode     = int(ep_match.group(2))
        title_part  = stem[: ep_match.start()]
    else:
        title_part = stem

    year: int | None = None
    year_match = _YEAR_PATTERN.search(title_part)
    if year_match:
        year       = int(year_match.group(1))
        title_part = title_part[: year_match.start()]

    title = _JUNK_CHARS.sub(" ", title_part).strip()

    return {
        "title":      title,
        "year":       year,
        "season":     season,
        "episode":    episode,
        "media_type": "episode" if (season is not None and episode is not None) else "movie",
    }
