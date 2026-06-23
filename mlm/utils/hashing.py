"""File hashing utilities used for duplicate detection.

Uses BLAKE2b (digest_size=20) instead of MD5:
  - No known collisions
  - ~3x faster than SHA-256 on modern CPUs
  - Available in stdlib; zero extra dependencies

Legacy ``partial_md5`` / ``full_md5`` names are kept as deprecated
aliases so existing callers continue to work during migration.
"""
import hashlib
import logging
from pathlib import Path

log = logging.getLogger(__name__)

CHUNK_SIZE    = 1024 * 1024        # 1 MB read chunks
PARTIAL_BYTES = 10 * 1024 * 1024  # first 10 MB for partial hash
_DIGEST_SIZE  = 20                 # 20 bytes = 40 hex chars


def partial_hash(file_path: str, limit_bytes: int = PARTIAL_BYTES) -> str:
    """Return a BLAKE2b hex digest of the first *limit_bytes* of *file_path*.

    Useful as a cheap pre-filter before computing a full hash.

    Raises:
        OSError: if the file cannot be read.
    """
    h = hashlib.blake2b(digest_size=_DIGEST_SIZE)
    remaining = limit_bytes
    with open(file_path, "rb") as f:
        while remaining > 0:
            chunk = f.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    digest = h.hexdigest()
    log.debug("partial_hash(%s) = %s", Path(file_path).name, digest)
    return digest


def full_hash(file_path: str) -> str:
    """Return a BLAKE2b hex digest of the entire file at *file_path*.

    Raises:
        OSError: if the file cannot be read.
    """
    h = hashlib.blake2b(digest_size=_DIGEST_SIZE)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    digest = h.hexdigest()
    log.debug("full_hash(%s) = %s", Path(file_path).name, digest)
    return digest


# ---------------------------------------------------------------------------
# Deprecated aliases — kept for backward compatibility during migration.
# New code should call partial_hash() / full_hash() directly.
# ---------------------------------------------------------------------------

def partial_md5(file_path: str, limit_bytes: int = PARTIAL_BYTES) -> str:  # noqa: D103
    """Deprecated: use partial_hash() instead."""
    import warnings
    warnings.warn(
        "partial_md5() is deprecated; use partial_hash() (BLAKE2b) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return partial_hash(file_path, limit_bytes)


def full_md5(file_path: str) -> str:  # noqa: D103
    """Deprecated: use full_hash() instead."""
    import warnings
    warnings.warn(
        "full_md5() is deprecated; use full_hash() (BLAKE2b) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return full_hash(file_path)
