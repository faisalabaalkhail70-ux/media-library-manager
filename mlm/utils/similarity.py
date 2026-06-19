from difflib import SequenceMatcher

def text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def duration_similarity(a: float | None, b: float | None, tolerance: float = 3.0) -> float:
    if a is None or b is None:
        return 0.0
    return 1.0 if abs(a - b) <= tolerance else 0.0

def size_similarity(a: int, b: int) -> float:
    if a <= 0 or b <= 0:
        return 0.0
    if a == b:
        return 1.0
    diff = abs(a - b)
    return max(0.0, 1.0 - (diff / max(a, b)))