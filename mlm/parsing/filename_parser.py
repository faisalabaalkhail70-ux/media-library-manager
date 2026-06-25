import os
import re
from dataclasses import dataclass
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
    stem, _ = os.path.splitext(file_name)
    cleaned = _cleanup_name(stem)

    for pattern in TV_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            # TV_PATTERNS already search the pre-cleaned string, so
            # match.group("show") is already clean.  Calling _cleanup_name()
            # again on the group result was redundant and could mangle
            # show titles that contain noise-adjacent words (issue #10).
            show = match.group("show").strip()
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
        # Same as above: the movie title group comes from an already-cleaned
        # string; a second _cleanup_name() pass is not needed.
        title = movie_match.group("title").strip()
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
