"""Tests for MetadataService input validation."""
import pytest
from unittest.mock import MagicMock


def _make_service():
    from mlm.services.metadata_service import MetadataService
    tmdb = MagicMock()
    entities_repo = MagicMock()
    return MetadataService(tmdb=tmdb, entities_repo=entities_repo), tmdb, entities_repo


def test_manual_match_rejects_negative_tmdb_id():
    svc, _, _ = _make_service()
    with pytest.raises(ValueError, match="tmdb_id must be a positive integer"):
        svc.manual_match_by_tmdb_id(1, -5, "movie")


def test_manual_match_rejects_unknown_media_type():
    svc, _, _ = _make_service()
    with pytest.raises(ValueError, match="media_type must be"):
        svc.manual_match_by_tmdb_id(1, 100, "anime")


def test_manual_match_movie_calls_tmdb():
    svc, tmdb, entities_repo = _make_service()
    tmdb.movie_details.return_value = {
        "title": "Inception", "release_date": "2010-07-16",
        "overview": "Dreams", "vote_average": 8.8,
        "genres": [], "poster_path": "/x.jpg", "id": 27205,
    }
    entities_repo.upsert_entity.return_value = 42
    result = svc.manual_match_by_tmdb_id(1, 27205, "movie")
    assert result["status"] == "matched"
    assert result["title"] == "Inception"
    entities_repo.link_file_to_entity.assert_called_once_with(1, 42)
