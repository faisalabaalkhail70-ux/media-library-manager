import re

MOVIE_YEAR_PATTERN = re.compile(r"^(?P<title>.*?)[\s\.\(\[]+(?P<year>19\d{2}|20\d{2})[\)\]]?", re.IGNORECASE)

TV_PATTERNS = [
    re.compile(r"^(?P<show>.+?)[\s\.\-_]+S(?P<season>\d{1,2})E(?P<episode>\d{1,3})", re.IGNORECASE),
    re.compile(r"^(?P<show>.+?)[\s\.\-_]+(?P<season>\d{1,2})x(?P<episode>\d{1,3})", re.IGNORECASE),
]

NOISE_TOKENS = {
    "1080p", "720p", "2160p", "4k", "bluray", "webrip", "web-dl",
    "x264", "x265", "h264", "h265", "hevc", "aac", "dts", "repack"
}