"""Similarity utilities for duplicate detection."""
import re
from difflib import SequenceMatcher


# ── Episode / season extraction ─────────────────────────────────────────────

_EP_RE = re.compile(r'[Ss](\d{1,2})[Ee](\d{1,2})')


def extract_episode_code(filename: str) -> tuple[int, int] | None:
    """Return (season, episode) if found in filename, else None."""
    m = _EP_RE.search(filename)
    return (int(m.group(1)), int(m.group(2))) if m else None


def same_episode(a: str, b: str) -> bool | None:
    """True = same SxxExx, False = different, None = no code found in either."""
    ca = extract_episode_code(a)
    cb = extract_episode_code(b)
    if ca is None or cb is None:
        return None   # movies / undetected — can't tell
    return ca == cb


# ── Filename normalisation ───────────────────────────────────────────────────

# Tags to strip before comparing names (release groups, codec labels, etc.)
_STRIP_RE = re.compile(
    r'\b('
    r'bluray|bdrip|webrip|web-dl|web|hdtv|dvdrip|remux|'
    r'x264|x265|hevc|h264|h265|avc|xvid|divx|'
    r'aac|ac3|dts|truehd|flac|mp3|eac3|atmos|'
    r'1080p|720p|480p|2160p|4k|uhd|hdr|sdr|dv|'
    r'proper|repack|extended|theatrical|directors.cut|'
    r'\d{4}'           # year
    r')\b',
    re.IGNORECASE,
)
_PUNC_RE = re.compile(r'[._\-\[\](){}]+')


def normalize_name(filename: str) -> str:
    """Strip extension, codec/quality tokens and punctuation for cleaner comparison."""
    # Remove extension
    name = re.sub(r'\.[a-zA-Z0-9]{2,5}$', '', filename)
    # Remove release group at the end  (e.g. "-KONTRAST")
    name = re.sub(r'-[A-Z0-9]{2,12}$', '', name, flags=re.IGNORECASE)
    name = _STRIP_RE.sub(' ', name)
    name = _PUNC_RE.sub(' ', name)
    return name.strip().lower()


# ── Core similarity functions ────────────────────────────────────────────────

def text_similarity(a: str, b: str) -> float:
    """Normalised name similarity (0-1)."""
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def duration_similarity(a: float | None, b: float | None, tolerance: float = 60.0) -> float:
    """Graduated duration score.

    - Within 3 s  → 1.0   (identical encode)
    - Within 60 s → linear decay from 1.0 → 0.5
    - > 60 s      → 0.0
    """
    if a is None or b is None:
        return 0.5   # unknown — neutral instead of hard-zero
    diff = abs(a - b)
    if diff <= 3:
        return 1.0
    if diff <= tolerance:
        return round(1.0 - 0.5 * (diff - 3) / (tolerance - 3), 3)
    return 0.0


def size_similarity(a: int, b: int) -> float:
    if a <= 0 or b <= 0:
        return 0.0
    if a == b:
        return 1.0
    diff = abs(a - b)
    return round(max(0.0, 1.0 - (diff / max(a, b))), 3)
