"""File hashing utilities for duplicate detection.

Changes in v1.1
---------------
* MD5 replaced with BLAKE2b (digest_size=20 -> 40-char hex string).
  BLAKE2b has no known collisions, is ~3x faster than SHA-256, and is
  recommended for file integrity checking.
* HASH_ALGO constant exported so the DB hash_algo column stays in sync.
* Old partial_md5 / full_md5 names kept as deprecated aliases so existing
  call-sites do not break before they are migrated.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

log = logging.getLogger(__name__)

CHUNK_SIZE: int = 1024 * 1024        # 1 MiB read buffer
PARTIAL_BYTES: int = 10 * 1024 * 1024  # first 10 MiB for quick-hash
HASH_ALGO: str = "blake2b-20"         # store this in the DB hash_algo column


def partial_blake2b(file_path: str | Path, limit_bytes: int = PARTIAL_BYTES) -> str:
    """Return a BLAKE2b hex digest of the first *limit_bytes* of *file_path*."""
    h = hashlib.blake2b(digest_size=20)
    remaining = limit_bytes
    with open(file_path, "rb") as fh:
        while remaining > 0:
            chunk = fh.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    return h.hexdigest()


def full_blake2b(file_path: str | Path) -> str:
    """Return a BLAKE2b hex digest of the entire *file_path*."""
    h = hashlib.blake2b(digest_size=20)
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Deprecated aliases — remove after all call-sites are migrated to blake2b
# ---------------------------------------------------------------------------

def partial_md5(file_path: str | Path, limit_bytes: int = PARTIAL_BYTES) -> str:
    """Deprecated: use partial_blake2b() instead."""
    log.warning("partial_md5() is deprecated; switch to partial_blake2b().")
    return partial_blake2b(file_path, limit_bytes)


def full_md5(file_path: str | Path) -> str:
    """Deprecated: use full_blake2b() instead."""
    log.warning("full_md5() is deprecated; switch to full_blake2b().")
    return full_blake2b(file_path)
