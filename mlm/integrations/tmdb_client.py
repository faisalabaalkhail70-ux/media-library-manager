"""TMDB API client with caching and secure key handling."""
import logging
import time
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PySide6.QtCore import QThread

from mlm.db.repositories.cache_repo import CacheRepository
from mlm.db.repositories.settings_repo import SettingsRepository

log = logging.getLogger(__name__)


def _build_session() -> requests.Session:
    """Return a Session with automatic retries on transient errors."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist={429, 500, 502, 503, 504},
        allowed_methods={"GET"},
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


class TMDBClient:
    """Thin wrapper around the TMDB v3 REST API.

    The API key is read from the DB settings table and sent as a Bearer
    token header — never as a URL query parameter — to prevent it from
    appearing in logs or proxy traces.

    The key is cached after the first successful DB read to avoid a DB
    round-trip on every single request during large metadata batches.
    Call ``invalidate_api_key_cache()`` from SettingsView whenever the
    user saves a new key.
    """

    BASE_URL = "https://api.themoviedb.org/3"
    _RATE_LIMIT_DELAY = 0.26          # TMDB allows ~4 req/s on free tier
    _THROTTLE_STEP_MS = 50            # granularity for interruptible sleep

    def __init__(
        self,
        settings: SettingsRepository | None = None,
        cache: CacheRepository | None = None,
    ) -> None:
        self.settings = settings or SettingsRepository()
        self.cache = cache or CacheRepository()
        self._session = _build_session()
        self._last_request_at: float = 0.0
        self._cached_api_key: str | None = None

    # ------------------------------------------------------------------
    # API key
    # ------------------------------------------------------------------

    def _api_key(self) -> str:
        """Return the TMDB API key, reading from DB only on first call."""
        if not self._cached_api_key:
            key = self.settings.get("tmdb_api_key", "").strip()
            if not key:
                raise RuntimeError(
                    "TMDB API key is not configured. "
                    "Go to Settings and enter your key."
                )
            self._cached_api_key = key
        return self._cached_api_key

    def invalidate_api_key_cache(self) -> None:
        """Drop the cached key so the next call re-reads it from the DB.

        Call this from SettingsView whenever the user saves a new key.
        """
        self._cached_api_key = None

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _throttle(self, running_flag_fn=None) -> None:
        """Sleep in short increments to respect TMDB rate limits.

        Uses ``QThread.msleep`` in *_THROTTLE_STEP_MS* ms increments
        instead of a single ``time.sleep`` call so that a worker\'s
        ``stop()`` signal can be honoured during the wait window.

        Args:
            running_flag_fn: Optional callable that returns ``False`` when
                the calling worker has been stopped.  If it returns
                ``False`` during the wait, ``InterruptedError`` is raised.
        """
        elapsed = time.monotonic() - self._last_request_at
        remaining_ms = int((self._RATE_LIMIT_DELAY - elapsed) * 1000)
        if remaining_ms > 0:
            slept = 0
            while slept < remaining_ms:
                if running_flag_fn is not None and not running_flag_fn():
                    raise InterruptedError("Worker stopped during TMDB throttle wait")
                step = min(self._THROTTLE_STEP_MS, remaining_ms - slept)
                QThread.msleep(step)
                slept += step
        self._last_request_at = time.monotonic()

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict, running_flag_fn=None) -> dict:
        """Fetch *path* with *params*, using DB cache to avoid repeat calls."""
        cache_key = f"{path}?{urlencode(sorted(params.items()))}"
        cached = self.cache.get_json("tmdb", cache_key)
        if cached is not None:
            log.debug("TMDB cache hit: %s", cache_key)
            return cached

        self._throttle(running_flag_fn)
        headers = {"Authorization": f"Bearer {self._api_key()}"}
        url = f"{self.BASE_URL}{path}"
        log.debug("TMDB GET %s params=%s", path, params)

        response = self._session.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        payload: dict = response.json()

        self.cache.set_json("tmdb", cache_key, payload)
        return payload

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def search_movie(self, title: str, year: int | None = None) -> dict:
        """Search TMDB for a movie by title and optional release year."""
        params: dict = {"query": title}
        if year:
            params["primary_release_year"] = year
        return self._get("/search/movie", params)

    def search_tv(self, title: str) -> dict:
        """Search TMDB for a TV show by title."""
        return self._get("/search/tv", {"query": title})

    def movie_details(self, tmdb_id: int) -> dict:
        """Fetch full movie details for *tmdb_id*."""
        return self._get(f"/movie/{tmdb_id}", {})

    def tv_details(self, tmdb_id: int) -> dict:
        """Fetch full TV show details for *tmdb_id*."""
        return self._get(f"/tv/{tmdb_id}", {})

    def tv_season_details(self, tmdb_id: int, season_number: int) -> dict:
        """Fetch details for a specific season of a TV show."""
        return self._get(f"/tv/{tmdb_id}/season/{season_number}", {})
