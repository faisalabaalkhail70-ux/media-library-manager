"""TMDB HTTP client.

Changes in v1.1
---------------
* API key cached lazily after first DB read — no more per-request DB hit.
  Call invalidate_api_key_cache() from SettingsView after saving a new key.
* _throttle() uses 50 ms polling increments (QThread.msleep) instead of
  time.sleep() so stop() signals are honoured during the delay window.
* Accepts optional running_flag callable for cooperative cancellation.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from typing import Callable

from PySide6.QtCore import QThread

from mlm.db.repositories.settings_repo import SettingsRepository

log = logging.getLogger(__name__)

_BASE_URL = "https://api.themoviedb.org/3"
_RATE_LIMIT_DELAY = 0.26  # ~4 req/s  (TMDB allows 40 req / 10 s)


class TMDBClient:
    """Thin wrapper around the TMDB v3 REST API."""

    def __init__(
        self,
        settings: SettingsRepository | None = None,
        running_flag: Callable[[], bool] | None = None,
    ) -> None:
        self._settings       = settings or SettingsRepository()
        self._running_flag   = running_flag
        self._last_request_at: float = 0.0
        self._cached_api_key: str | None = None

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------

    def _api_key(self) -> str:
        """Return the cached API key, reading from DB only on first call."""
        if not self._cached_api_key:
            key = (self._settings.get("tmdb_api_key") or "").strip()
            if not key:
                raise RuntimeError(
                    "TMDB API key is not configured.\n"
                    "Go to Settings → Integrations and enter your Read Access Token."
                )
            self._cached_api_key = key
        return self._cached_api_key

    def invalidate_api_key_cache(self) -> None:
        """Call from SettingsView after the user saves a new API key."""
        self._cached_api_key = None

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _throttle(self) -> None:
        """Sleep in 50 ms increments so stop() signals are not blocked."""
        elapsed = time.monotonic() - self._last_request_at
        remaining_ms = int((_RATE_LIMIT_DELAY - elapsed) * 1000)
        if remaining_ms > 0:
            slept = 0
            while slept < remaining_ms:
                if self._running_flag is not None and not self._running_flag():
                    raise InterruptedError("TMDBClient: worker stopped during throttle")
                QThread.msleep(min(50, remaining_ms - slept))
                slept += 50
        self._last_request_at = time.monotonic()

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        self._throttle()
        token = self._api_key()
        qs  = urllib.parse.urlencode(params or {})
        url = f"{_BASE_URL}{endpoint}{'?' + qs if qs else ''}"
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ------------------------------------------------------------------
    # Public endpoints
    # ------------------------------------------------------------------

    def search_movie(self, query: str, year: int | None = None) -> dict:
        params: dict = {"query": query, "include_adult": "false"}
        if year:
            params["year"] = str(year)
        return self._get("/search/movie", params)

    def search_tv(self, query: str) -> dict:
        return self._get("/search/tv", {"query": query, "include_adult": "false"})

    def get_movie_details(self, tmdb_id: int) -> dict:
        return self._get(f"/movie/{tmdb_id}", {"append_to_response": "credits,videos"})

    def get_tv_details(self, tmdb_id: int) -> dict:
        return self._get(f"/tv/{tmdb_id}", {"append_to_response": "credits,videos"})

    def get_season_details(self, series_id: int, season_number: int) -> dict:
        return self._get(f"/tv/{series_id}/season/{season_number}")
