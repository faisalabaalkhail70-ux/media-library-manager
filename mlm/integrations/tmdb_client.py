import requests
from urllib.parse import urlencode

from mlm.db.repositories.cache_repo import CacheRepository
from mlm.db.repositories.settings_repo import SettingsRepository

class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self) -> None:
        self.settings = SettingsRepository()
        self.cache = CacheRepository()

    def _api_key(self) -> str:
        return self.settings.get("tmdb_api_key", "").strip()

    def _get(self, path: str, params: dict) -> dict:
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError("TMDB API key is not configured.")

        query = {"api_key": api_key, **params}
        cache_key = f"{path}?{urlencode(sorted(query.items()))}"
        cached = self.cache.get_json("tmdb", cache_key)
        if cached is not None:
            return cached

        response = requests.get(f"{self.BASE_URL}{path}", params=query, timeout=10)
        response.raise_for_status()
        payload = response.json()
        self.cache.set_json("tmdb", cache_key, payload)
        return payload

    def search_movie(self, title: str, year: int | None = None) -> dict:
        params = {"query": title}
        if year:
            params["primary_release_year"] = year
        return self._get("/search/movie", params)

    def search_tv(self, title: str) -> dict:
        return self._get("/search/tv", {"query": title})

    def movie_details(self, tmdb_id: int) -> dict:
        return self._get(f"/movie/{tmdb_id}", {})

    def tv_details(self, tmdb_id: int) -> dict:
        return self._get(f"/tv/{tmdb_id}", {})

    def tv_season_details(self, tmdb_id: int, season_number: int) -> dict:
        return self._get(f"/tv/{tmdb_id}/season/{season_number}", {})