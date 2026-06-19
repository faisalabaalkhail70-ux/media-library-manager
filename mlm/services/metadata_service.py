import json
from mlm.db.connection import get_connection
from mlm.db.repositories.entities_repo import EntitiesRepository
from mlm.integrations.tmdb_client import TMDBClient
from mlm.parsing.filename_parser import parse_media_filename

class MetadataService:
    def __init__(self) -> None:
        self.tmdb = TMDBClient()
        self.entities_repo = EntitiesRepository()

    def list_unmatched_files(self, limit: int = 500) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, file_name, file_path
                FROM media_files
                WHERE entity_id IS NULL AND removed_at IS NULL
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def auto_match_file(self, media_file_id: int, file_name: str) -> dict:
        parsed = parse_media_filename(file_name)

        if parsed.media_type == "movie":
            results = self.tmdb.search_movie(parsed.title or "", parsed.year)
            best = (results.get("results") or [None])[0]
            if not best:
                return {"status": "unmatched", "reason": "No movie results"}

            details = self.tmdb.movie_details(best["id"])
            entity_id = self.entities_repo.upsert_entity(
                media_type="movie",
                title=details.get("title") or parsed.title or file_name,
                release_year=int(details["release_date"][:4]) if details.get("release_date") else parsed.year,
                tmdb_id=details.get("id"),
                plot=details.get("overview"),
                rating=details.get("vote_average"),
                genres_json=json.dumps(details.get("genres", [])),
                poster_path=details.get("poster_path"),
                metadata_json=json.dumps(details),
            )
            self.entities_repo.link_file_to_entity(media_file_id, entity_id)
            return {"status": "matched", "media_type": "movie", "title": details.get("title")}

        if parsed.media_type == "episode":
            results = self.tmdb.search_tv(parsed.show_title or "")
            best = (results.get("results") or [None])[0]
            if not best:
                return {"status": "unmatched", "reason": "No TV results"}

            details = self.tmdb.tv_details(best["id"])
            entity_id = self.entities_repo.upsert_entity(
                media_type="show",
                title=details.get("name") or parsed.show_title or file_name,
                release_year=int(details["first_air_date"][:4]) if details.get("first_air_date") else None,
                tmdb_id=details.get("id"),
                plot=details.get("overview"),
                rating=details.get("vote_average"),
                genres_json=json.dumps(details.get("genres", [])),
                poster_path=details.get("poster_path"),
                metadata_json=json.dumps(details),
            )
            self.entities_repo.link_file_to_entity(media_file_id, entity_id)

            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO episodes (
                        entity_id, media_file_id, season_number, episode_number, is_missing
                    )
                    VALUES (?, ?, ?, ?, 0)
                    ON CONFLICT(entity_id, season_number, episode_number)
                    DO UPDATE SET media_file_id=excluded.media_file_id, is_missing=0
                    """,
                    (entity_id, media_file_id, parsed.season_number, parsed.episode_number),
                )

            return {
                "status": "matched",
                "media_type": "show",
                "title": details.get("name"),
                "season": parsed.season_number,
                "episode": parsed.episode_number,
            }

        return {"status": "skipped", "reason": "Unknown filename format"}

    def manual_match_by_tmdb_id(self, media_file_id: int, tmdb_id: int, media_type: str) -> dict:
        if media_type == "movie":
            details = self.tmdb.movie_details(tmdb_id)
            title = details.get("title")
            year = int(details["release_date"][:4]) if details.get("release_date") else None
        else:
            details = self.tmdb.tv_details(tmdb_id)
            title = details.get("name")
            year = int(details["first_air_date"][:4]) if details.get("first_air_date") else None

        entity_id = self.entities_repo.upsert_entity(
            media_type="movie" if media_type == "movie" else "show",
            title=title or f"TMDB {tmdb_id}",
            release_year=year,
            tmdb_id=tmdb_id,
            plot=details.get("overview"),
            rating=details.get("vote_average"),
            genres_json=json.dumps(details.get("genres", [])),
            poster_path=details.get("poster_path"),
            metadata_json=json.dumps(details),
        )
        self.entities_repo.link_file_to_entity(media_file_id, entity_id)
        return {"status": "matched", "title": title, "tmdb_id": tmdb_id}