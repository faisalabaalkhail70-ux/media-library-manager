"""TMDB API client with caching and secure key handling.

.. note:: Threading contract
   Every method on this class that makes an HTTP request (``_get``, and all
   public helpers that call it) MUST be invoked from a ``QThread`` worker
   thread, never from the Qt main / GUI thread.

   ``_throttle()`` calls ``time.sleep()`` which **blocks the calling thread**.
   Calling it on the main thread freezes the entire GUI for up to
   ``_RATE_LIMIT_DELAY`` seconds per request (issue #14).

   The correct pattern is::

       class MetadataWorker(QThread):
           def run(self):
               client = TMDBClient()
               result = client.search_movie("Inception", 2010)  # safe here

   Never call ``TMDBClient`` methods directly in a slot or event handler on
   the main thread.
"""
import logging
import time
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

    .. warning::
        All public methods block on ``time.sleep()`` inside ``_throttle()``.
        See the module-level note for the mandatory threading contract.
    """

    BASE_URL = "https://api.themoviedb.org/3"
    _RATE_LIMIT_DELAY = 0.26  # TMDB allows ~4 req/s on free tier

    def __init__(
        self,
        settings: SettingsRepository | None = None,
        cache: CacheRepository | None = None,
    ) -> None:
        self.settings = settings or SettingsRepository()
        self.cache = cache or CacheRepository()
        self._session = _build_session()
        self._last_request_at: float = 0.0

    def _api_key(self) -> str:
        key = self.settings.get("tmdb_api_key", "").strip()
        if not key:
            raise RuntimeError(
                "TMDB API key is not configured. "
                "Go to Settings and enter your key."
            )
        return key

    def _throttle(self) -> None:
        """Ensure we respect TMDB rate limits.

        .. warning::
            This method calls ``time.sleep()`` and **blocks the calling
            thread**.  It MUST only be called from a ``QThread`` worker.
            Calling it from the Qt main thread will freeze the GUI (issue #14).
        """
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._RATE_LIMIT_DELAY:
            time.sleep(self._RATE_LIMIT_DELAY - elapsed)
        self._last_request_at = time.monotonic()

    def _get(self, path: str, params: dict) -> dict:
        """Fetch *path* with *params*, using DB cache to avoid repeat calls."""
        cache_key = f"{path}?{urlencode(sorted(params.items()))}"
        cached = self.cache.get_json("tmdb", cache_key)
        if cached is not None:
            log.debug("TMDB cache hit: %s", cache_key)
            return cached

        self._throttle()
        headers = {"Authorization": f"Bearer {self._api_key()}"}
        url = f"{self.BASE_URL}{path}"
        log.debug("TMDB GET %s params=%s", path, params)

        response = self._session.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        payload: dict = response.json()

        self.cache.set_json("tmdb", cache_key, payload)
        return payload

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
