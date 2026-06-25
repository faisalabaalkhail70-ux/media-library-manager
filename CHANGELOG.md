# Changelog

## [v1.0.6] — 2026-06-25

### Fixed

#### Section 1 — Critical Bugs
- **`mlm/db/schema.py`** — `executescript()` DDL now runs on a bare connection outside `get_connection()` to prevent the implicit `COMMIT` it issues from escaping the `schema_version` write transaction.
- **`mlm/services/rename_service.py`** — Separated ledger writes and DB path updates into their own isolated transactions; previously two different connection objects were mixed inside the same logical operation.
- **`mlm/services/health_service.py`** — `VALID_EXTS` is now derived directly from `AppConfig().supported_video_exts` instead of a hard-coded frozenset that could drift out of sync with `config.py`.
- **`mlm/services/duplicate_service.py`** — Fixed stale ID exclusion: `ignored_ids` and `used_ids` are now captured in-memory immediately after `clear_non_ignored_groups()`, before any new groups are written, preventing valid candidates from being silently excluded.
- **`mlm/db/repositories/entities_repo.py`** — Replaced the non-atomic SELECT-then-INSERT/UPDATE pattern with a single `INSERT ... ON CONFLICT DO UPDATE ... RETURNING id` statement, eliminating a race condition that caused UNIQUE constraint violations under concurrent access.

#### Section 2 — Logic Issues & Incorrect Linking
- **`mlm/services/export_service.py`** — PDF exports now redraw the report title, divider, and column headers after every `showPage()` call; previously pages 2+ had no context headers.
- **`mlm/services/duplicate_service.py`** — Removed unused `same_episode` import from `mlm.utils.similarity`.
- **`mlm/services/metadata_service.py`** — Removed redundant `import json as _json` inside `refresh_entity()`; the module-level `import json` already covers all usages.
- **`mlm/parsing/plex_patterns.py`** — `MOVIE_YEAR_PATTERN` title group changed from `.*?` to `.+?` to prevent matching an empty title when a filename begins with a year-like number.
- **`mlm/parsing/filename_parser.py`** — Removed redundant second `_cleanup_name()` call on regex match group results; groups are already extracted from the pre-cleaned string.
- **`mlm/services/scan_service.py`** — Added `warnings_count: int = 0` parameter to `finish_scan_run()` and included it in the `UPDATE` statement; previously the schema column was always left at `0`.

#### Section 3 — Improvements & Best Practices
- **`mlm/db/connection.py`** — Added `Generator[sqlite3.Connection, None, None]` return-type annotation to `get_connection()` for full mypy/Pyright compatibility.
- **`mlm/db/repositories/files_repo.py`** — Changed `fetch_library_rows()` default from `limit=5000` to `limit=0` (fetch all); the `LIMIT` clause is now omitted entirely for unlimited fetches, preventing silent truncation of large libraries.
- **`mlm/integrations/tmdb_client.py`** — Added module-level and method-level docstring warnings making the mandatory `QThread` contract explicit; `_throttle()` calls `time.sleep()` and must never be called from the Qt main thread.
- **`scripts/remove_pycache.sh`** — Added helper script to untrack any committed `__pycache__` directories and compiled bytecode files via `git rm -r --cached`.

---

## [v1.0.5] — prior release
