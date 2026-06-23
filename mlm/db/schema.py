"""Database schema definition and initialisation — v1.2.

New tables in v1.2 (schema version 5):
  subtitle_files      H-2  subtitle tracking
  file_notes          R-4  per-file notes & tags
  library_snapshots   R-6  snapshot header
  snapshot_files      R-6  per-file snapshot rows
  scheduled_tasks     E-3  APScheduler job persistence metadata
  codec_upgrade_log   R-3  codec quality upgrade tracking
  action_cards        H-4  health action cards

New columns in v1.2:
  media_entities.manually_verified  (from v1.1 review)
  media_files.moved_to_path         folder-restructure audit trail
"""
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
    manually_verified INTEGER NOT NULL DEFAULT 0,
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
    moved_to_path TEXT,
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

CREATE TABLE IF NOT EXISTS watchlist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id  INTEGER NOT NULL UNIQUE,
    priority   INTEGER NOT NULL DEFAULT 5,
    notes      TEXT,
    added_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    watched_at TEXT,
    FOREIGN KEY(entity_id) REFERENCES media_entities(id) ON DELETE CASCADE
);

-- v1.2 ---------------------------------------------------------------

-- H-2: Subtitle file tracking
CREATE TABLE IF NOT EXISTS subtitle_files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    media_file_id   INTEGER NOT NULL,
    file_path       TEXT NOT NULL UNIQUE,
    language        TEXT,
    format          TEXT,
    is_forced       INTEGER NOT NULL DEFAULT 0,
    is_sdh          INTEGER NOT NULL DEFAULT 0,
    file_size_bytes INTEGER,
    discovered_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    removed_at      TEXT,
    FOREIGN KEY(media_file_id) REFERENCES media_files(id) ON DELETE CASCADE
);

-- R-4: Per-file notes & tags
CREATE TABLE IF NOT EXISTS file_notes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    media_file_id INTEGER NOT NULL UNIQUE,
    note          TEXT,
    tags          TEXT,     -- comma-separated tag list
    updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(media_file_id) REFERENCES media_files(id) ON DELETE CASCADE
);

-- R-6: Library snapshots
CREATE TABLE IF NOT EXISTS library_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    label       TEXT,
    taken_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    file_count  INTEGER NOT NULL DEFAULT 0,
    total_bytes INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS snapshot_files (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id      INTEGER NOT NULL,
    media_file_id    INTEGER NOT NULL,
    file_path        TEXT NOT NULL,
    file_size_bytes  INTEGER NOT NULL,
    entity_title     TEXT,
    health_status    TEXT,
    video_codec      TEXT,
    FOREIGN KEY(snapshot_id) REFERENCES library_snapshots(id) ON DELETE CASCADE
);

-- E-3: APScheduler job metadata (mirrors job store state for display)
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id       TEXT NOT NULL UNIQUE,
    task_type    TEXT NOT NULL,
    cron_expr    TEXT,
    interval_min INTEGER,
    is_enabled   INTEGER NOT NULL DEFAULT 1,
    last_run_at  TEXT,
    last_status  TEXT,
    next_run_at  TEXT,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- R-3: Codec upgrade tracker
CREATE TABLE IF NOT EXISTS codec_upgrade_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    media_file_id   INTEGER NOT NULL,
    old_video_codec TEXT,
    new_video_codec TEXT,
    old_resolution  TEXT,
    new_resolution  TEXT,
    upgrade_type    TEXT,   -- 'codec', 'resolution', 'both'
    detected_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    applied_at      TEXT,
    FOREIGN KEY(media_file_id) REFERENCES media_files(id) ON DELETE CASCADE
);

-- H-4: Health action cards
CREATE TABLE IF NOT EXISTS action_cards (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    card_type     TEXT NOT NULL,
    severity      TEXT NOT NULL DEFAULT 'info',  -- 'critical','warning','info'
    title         TEXT NOT NULL,
    description   TEXT,
    media_file_id INTEGER,
    payload_json  TEXT,
    status        TEXT NOT NULL DEFAULT 'open',  -- 'open','dismissed','resolved'
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at   TEXT,
    FOREIGN KEY(media_file_id) REFERENCES media_files(id) ON DELETE SET NULL
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
CREATE INDEX IF NOT EXISTS idx_subtitles_file      ON subtitle_files(media_file_id);
CREATE INDEX IF NOT EXISTS idx_notes_file          ON file_notes(media_file_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_files_snap ON snapshot_files(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_action_cards_status ON action_cards(status);
CREATE INDEX IF NOT EXISTS idx_codec_log_file      ON codec_upgrade_log(media_file_id);
"""

CURRENT_VERSION = 5

_MIGRATIONS: dict[int, list[str]] = {
    5: [
        # Add manually_verified to media_entities if upgrading from v4
        "ALTER TABLE media_entities ADD COLUMN manually_verified INTEGER NOT NULL DEFAULT 0",
        # Add moved_to_path to media_files
        "ALTER TABLE media_files ADD COLUMN moved_to_path TEXT",
    ],
}


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def init_database() -> None:
    """Initialise schema and apply any outstanding migrations."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        row      = conn.execute("SELECT version FROM schema_version").fetchone()
        existing = row["version"] if row else 0

        if existing < CURRENT_VERSION:
            for ver in range(existing + 1, CURRENT_VERSION + 1):
                stmts = _MIGRATIONS.get(ver, [])
                for stmt in stmts:
                    try:
                        conn.execute(stmt)
                        log.info("Migration v%d applied: %s", ver, stmt[:60])
                    except Exception as exc:  # noqa: BLE001
                        # Column may already exist on fresh installs
                        log.debug("Migration v%d skipped (%s): %s", ver, exc, stmt[:60])
            conn.execute(
                "INSERT OR REPLACE INTO schema_version(version) VALUES (?)",
                (CURRENT_VERSION,),
            )
            log.info("Schema upgraded from v%d to v%d", existing, CURRENT_VERSION)
