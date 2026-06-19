from mlm.db.connection import get_connection

SCHEMA_SQL = """
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
    cache_key TEXT NOT NULL UNIQUE,
    response_json TEXT NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT
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
"""

def init_database() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)