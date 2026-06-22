"""File hashing utilities used for duplicate detection."""
import hashlib
import logging
from pathlib import Path

log = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024       # 1 MB read chunks
PARTIAL_BYTES = 10 * 1024 * 1024  # Read only first 10 MB for partial hash


def partial_md5(file_path: str, limit_bytes: int = PARTIAL_BYTES) -> str:
    """Return an MD5 hex digest of the first *limit_bytes* of *file_path*.

    Useful as a cheap pre-filter before computing a full hash.

    Raises:
        OSError: if the file cannot be read.
    """
    h = hashlib.md5(usedforsecurity=False)
    remaining = limit_bytes
    with open(file_path, "rb") as f:
        while remaining > 0:
            chunk = f.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    digest = h.hexdigest()
    log.debug("partial_md5(%s) = %s", Path(file_path).name, digest)
    return digest


def full_md5(file_path: str) -> str:
    """Return an MD5 hex digest of the entire file at *file_path*.

    Raises:
        OSError: if the file cannot be read.
    """
    h = hashlib.md5(usedforsecurity=False)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    digest = h.hexdigest()
    log.debug("full_md5(%s) = %s", Path(file_path).name, digest)
    return digest
