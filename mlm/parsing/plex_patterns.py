import re

# `.+?` (one-or-more, lazy) replaces the previous `.*?` (zero-or-more).
# This guards against the edge case where a filename starts with a year-like
# number (e.g. '2001 A Space Odyssey.mkv'), which caused `.*?` to match an
# empty string for the title group before consuming the year digits (issue #9).
MOVIE_YEAR_PATTERN = re.compile(
    r"^(?P<title>.+?)[\s\.\(\[]+(?P<year>19\d{2}|20\d{2})[\)\]]?",
    re.IGNORECASE,
)

TV_PATTERNS = [
    # S01E02 / S01E02E03
    re.compile(
        r"(?P<show>.*?)[\s\._\-]+[Ss](?P<season>\d{1,2})[Ee](?P<episode>\d{1,2})",
        re.IGNORECASE,
    ),
    # 1x02
    re.compile(
        r"(?P<show>.*?)[\s\._\-]+(?P<season>\d{1,2})x(?P<episode>\d{2})",
        re.IGNORECASE,
    ),
]

NOISE_TOKENS: frozenset[str] = frozenset({
    "bluray", "blu-ray", "bdrip", "brrip", "webrip", "web-dl", "web",
    "hdtv", "dvdrip", "dvd", "1080p", "720p", "480p", "2160p", "4k",
    "uhd", "hdr", "x264", "x265", "h264", "h265", "hevc", "avc",
    "xvid", "divx", "aac", "ac3", "dts", "ddp", "atmos", "truehd",
    "flac", "mp3", "remux", "repack", "proper", "extended", "theatrical",
    "yts", "rarbg", "ettv",
})
