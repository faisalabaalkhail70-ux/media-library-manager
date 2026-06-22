"""Tests for DuplicateService hash-bucketing logic."""
from unittest.mock import MagicMock, patch


def _make_service():
    from mlm.services.duplicate_service import DuplicateService
    repo = MagicMock()
    files_repo = MagicMock()
    svc = DuplicateService(repo=repo, files_repo=files_repo)
    return svc, repo, files_repo


def test_exact_duplicate_detected():
    """Two files with the same size and hash must form an exact group."""
    svc, repo, files_repo = _make_service()
    repo.create_group.return_value = 1

    files = [
        {"id": 1, "file_name": "movie.mkv", "file_path": "/a/movie.mkv",
         "file_size_bytes": 1000, "duration_seconds": 7200,
         "partial_hash": "abc", "full_hash": "xyz",
         "resolution": "1080p", "video_codec": "h264"},
        {"id": 2, "file_name": "movie.mkv", "file_path": "/b/movie.mkv",
         "file_size_bytes": 1000, "duration_seconds": 7200,
         "partial_hash": "abc", "full_hash": "xyz",
         "resolution": "1080p", "video_codec": "h264"},
    ]
    count = svc._build_exact_duplicates(files)
    assert count == 1
    repo.create_group.assert_called_once_with("exact", 1.0)


def test_different_size_no_exact_group():
    """Files with different sizes must not be grouped as exact duplicates."""
    svc, repo, files_repo = _make_service()
    files = [
        {"id": 1, "file_name": "a.mkv", "file_path": "/a.mkv",
         "file_size_bytes": 1000, "duration_seconds": 100,
         "partial_hash": None, "full_hash": None,
         "resolution": None, "video_codec": None},
        {"id": 2, "file_name": "b.mkv", "file_path": "/b.mkv",
         "file_size_bytes": 9999, "duration_seconds": 100,
         "partial_hash": None, "full_hash": None,
         "resolution": None, "video_codec": None},
    ]
    count = svc._build_exact_duplicates(files)
    assert count == 0
    repo.create_group.assert_not_called()
