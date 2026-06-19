from mlm.db.repositories.episodes_repo import EpisodesRepository
from mlm.integrations.tmdb_client import TMDBClient

class EpisodeService:
    def __init__(self) -> None:
        self.repo = EpisodesRepository()
        self.tmdb = TMDBClient()

    def check_show_missing(self, entity_id: int, tmdb_id: int) -> dict:
        self.repo.clear_missing_for_entity(entity_id)
        existing = self.repo.existing_episode_keys(entity_id)

        show = self.tmdb.tv_details(tmdb_id)
        total_missing = 0
        seasons_checked = 0

        for season in show.get("seasons", []):
            season_number = season.get("season_number")
            if season_number is None or season_number == 0:
                continue

            season_payload = self.tmdb.tv_season_details(tmdb_id, season_number)
            seasons_checked += 1

            for ep in season_payload.get("episodes", []):
                key = (season_number, int(ep.get("episode_number")))
                if key not in existing:
                    self.repo.upsert_missing_episode(
                        entity_id=entity_id,
                        season_number=season_number,
                        episode_number=int(ep.get("episode_number")),
                        episode_title=ep.get("name"),
                        air_date=ep.get("air_date"),
                        tmdb_episode_id=ep.get("id"),
                    )
                    total_missing += 1

        return {
            "show_title": show.get("name"),
            "seasons_checked": seasons_checked,
            "missing_count": total_missing,
        }

    def check_all_shows(self) -> list[dict]:
        results = []
        for show in self.repo.list_show_entities():
            results.append(self.check_show_missing(show["id"], show["tmdb_id"]))
        return results