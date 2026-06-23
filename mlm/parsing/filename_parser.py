"""Parse a media filename into a structured ``ParsedMediaName`` object."""
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from mlm.parsing.plex_patterns import MOVIE_YEAR_PATTERN, TV_PATTERNS, NOISE_TOKENS


@dataclass(slots=True)
class ParsedMediaName:
    media_type: str               # movie, episode, unknown
    raw_name: str
    title: str | None = None
    year: int | None = None
    show_title: str | None = None
    season_number: int | None = None
    episode_number: int | None = None


def _cleanup_name(name: str) -> str:
    name = name.replace(".", " ").replace("_", " ").strip()
    parts = [p for p in name.split() if p.lower() not in NOISE_TOKENS]
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def parse_media_filename(file_name: str) -> ParsedMediaName:
    # PurePosixPath.stem strips the extension the same way os.path.splitext
    # does, but is consistent with the pathlib style used throughout the project.
    stem = PurePosixPath(file_name).stem
    cleaned = _cleanup_name(stem)

    for pattern in TV_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            show = _cleanup_name(match.group("show"))
            return ParsedMediaName(
                media_type="episode",
                raw_name=file_name,
                show_title=show,
                title=show,
                season_number=int(match.group("season")),
                episode_number=int(match.group("episode")),
            )

    movie_match = MOVIE_YEAR_PATTERN.search(cleaned)
    if movie_match:
        title = _cleanup_name(movie_match.group("title"))
        year = int(movie_match.group("year"))
        return ParsedMediaName(
            media_type="movie",
            raw_name=file_name,
            title=title,
            year=year,
        )

    return ParsedMediaName(
        media_type="unknown",
        raw_name=file_name,
        title=cleaned,
    )
