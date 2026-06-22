"""Database schema definition and initialisation."""
import logging
from mlm.db.connection import get_connection

log = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS directories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    library_type TEXT NOT NULL DEFAULT 'mixed',
    is_enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_scanned_at TEXT
);

CREATE TABLE IF NOT EXISTS media_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_type TEXT NOT NULL,
    title TEXT NOT NULL,
    sort_title TEXT,
    release_year INTEGER,
    tmdb_id INTEGER,
    plot TEXT,
    rating REAL,
    genres_json TEXT,
    poster_path TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(media_type, tmdb_id)
);

CREATE TABLE IF NOT EXISTS media_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER,
    directory_id INTEGER,
    file_path TEXT NOT NULL UNIQUE,
    parent_folder TEXT,
    file_name TEXT NOT NULL,
    extension TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    modified_at TEXT,
    discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    removed_at TEXT,
    partial_hash TEXT,
    full_hash TEXT,
    hash_algo TEXT,
    duration_seconds REAL,
    video_codec TEXT,
    audio_codec TEXT,
    resolution TEXT,
    width INTEGER,
    height INTEGER,
    bitrate INTEGER,
    container_format TEXT,
    is_missing INTEGER NOT NULL DEFAULT 0,
    health_status TEXT DEFAULT 'unknown',
    health_notes TEXT,
    FOREIGN KEY(entity_id) REFERENCES media_entities(id),
    FOREIGN KEY(directory_id) REFERENCES directories(id)
);

CREATE TABLE IF NOT EXISTS scan_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    directory_id INTEGER,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    files_seen INTEGER NOT NULL DEFAULT 0,
    files_added INTEGER NOT NULL DEFAULT 0,
    files_updated INTEGER NOT NULL DEFAULT 0,
    files_removed INTEGER NOT NULL DEFAULT 0,
    warnings_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    FOREIGN KEY(directory_id) REFERENCES directories(id)
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    cache_key TEXT NOT NULL,
    response_json TEXT NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT,
    UNIQUE(provider, cache_key)
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    media_file_id INTEGER,
    season_number INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    episode_title TEXT,
    air_date TEXT,
    tmdb_episode_id INTEGER,
    is_missing INTEGER NOT NULL DEFAULT 0,
    UNIQUE(entity_id, season_number, episode_number),
    FOREIGN KEY(entity_id) REFERENCES media_entities(id),
    FOREIGN KEY(media_file_id) REFERENCES media_files(id)
);

CREATE TABLE IF NOT EXISTS duplicate_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_type TEXT NOT NULL,
    confidence REAL,
    review_status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS duplicate_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    media_file_id INTEGER NOT NULL,
    score REAL,
    reason_json TEXT,
    FOREIGN KEY(group_id) REFERENCES duplicate_groups(id),
    FOREIGN KEY(media_file_id) REFERENCES media_files(id)
);

CREATE TABLE IF NOT EXISTS action_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    media_file_id INTEGER,
    old_path TEXT,
    new_path TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    undone_at TEXT,
    FOREIGN KEY(media_file_id) REFERENCES media_files(id)
);

-- Collections -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS collections (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collection_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL,
    entity_id     INTEGER NOT NULL,
    added_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(collection_id, entity_id),
    FOREIGN KEY(collection_id) REFERENCES collections(id) ON DELETE CASCADE,
    FOREIGN KEY(entity_id)     REFERENCES media_entities(id) ON DELETE CASCADE
);

-- Watchlist -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS watchlist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id  INTEGER NOT NULL UNIQUE,
    priority   INTEGER NOT NULL DEFAULT 5,   -- 1 (highest) to 10 (lowest)
    notes      TEXT,
    added_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    watched_at TEXT,                         -- NULL = not yet watched
    FOREIGN KEY(entity_id) REFERENCES media_entities(id) ON DELETE CASCADE
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_files_entity        ON media_files(entity_id);
CREATE INDEX IF NOT EXISTS idx_files_removed       ON media_files(removed_at);
CREATE INDEX IF NOT EXISTS idx_files_directory     ON media_files(directory_id);
CREATE INDEX IF NOT EXISTS idx_files_partial_h     ON media_files(partial_hash);
CREATE INDEX IF NOT EXISTS idx_files_full_h        ON media_files(full_hash);
CREATE INDEX IF NOT EXISTS idx_cache_provider      ON api_cache(provider, cache_key);
CREATE INDEX IF NOT EXISTS idx_episodes_entity     ON episodes(entity_id);
CREATE INDEX IF NOT EXISTS idx_episodes_missing    ON episodes(is_missing);
CREATE INDEX IF NOT EXISTS idx_col_items_col       ON collection_items(collection_id);
CREATE INDEX IF NOT EXISTS idx_col_items_entity    ON collection_items(entity_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_entity    ON watchlist(entity_id);
"""

CURRENT_VERSION = 4


def init_database() -> None:
    """Initialise schema and apply any outstanding migrations."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        existing = row["version"] if row else 0
        if existing < CURRENT_VERSION:
            conn.execute(
                "INSERT OR REPLACE INTO schema_version(version) VALUES (?)",
                (CURRENT_VERSION,),
            )
            log.info("Schema upgraded from version %d to %d", existing, CURRENT_VERSION)
