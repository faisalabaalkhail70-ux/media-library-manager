"""Tests for HashWorker mode validation and SQL injection prevention."""
import pytest
from unittest.mock import patch, MagicMock


def test_invalid_mode_raises():
    """HashWorker must reject unknown mode strings."""
    with patch("mlm.workers.hash_worker.FilesRepository"):
        from mlm.workers.hash_worker import HashWorker
        with pytest.raises(ValueError, match="Invalid hash mode"):
            HashWorker(mode="DROP TABLE media_files--")


def test_valid_modes_accepted():
    """Both accepted modes must not raise on construction."""
    with patch("mlm.workers.hash_worker.FilesRepository"):
        from mlm.workers.hash_worker import HashWorker
        HashWorker(mode="partial")
        HashWorker(mode="full")
