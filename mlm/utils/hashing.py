import hashlib

CHUNK_SIZE = 1024 * 1024
PARTIAL_BYTES = 10 * 1024 * 1024

def partial_md5(file_path: str, limit_bytes: int = PARTIAL_BYTES) -> str:
    h = hashlib.md5()
    remaining = limit_bytes
    with open(file_path, "rb") as f:
        while remaining > 0:
            chunk = f.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    return h.hexdigest()

def full_md5(file_path: str) -> str:
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()