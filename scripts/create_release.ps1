# Run this script from the repo root in PowerShell:
#   .\scripts\create_release.ps1
#
# Requires gh CLI to be installed and authenticated.
# If 'gh' is not found, close and reopen PowerShell after installing it.

$notes = @"
## v1.0.6 - Code Quality & Bug Fix Release

### Critical Fixes
- **schema.py** - Fixed executescript() breaking transaction safety on DB init
- **rename_service.py** - Fixed mixed connection objects causing inconsistent ledger/DB state
- **health_service.py** - VALID_EXTS now sourced from AppConfig (no more config drift)
- **duplicate_service.py** - Fixed stale ID exclusion silently dropping valid duplicate candidates
- **entities_repo.py** - Race condition on concurrent upsert replaced with atomic ON CONFLICT DO UPDATE

### Logic & Linking Fixes
- **export_service.py** - PDF pages 2+ now correctly show report title and column headers
- **duplicate_service.py** - Removed unused same_episode import
- **metadata_service.py** - Removed redundant import json as _json inside refresh_entity()
- **plex_patterns.py** - Regex title group now requires 1+ characters (prevents empty match)
- **filename_parser.py** - Removed double _cleanup_name() call on already-clean regex groups
- **scan_service.py** - warnings_count is now written to DB after every scan run

### Improvements
- **connection.py** - get_connection() now has full Generator return-type annotation
- **files_repo.py** - fetch_library_rows() default changed to limit=0 (fetch all, no silent truncation)
- **tmdb_client.py** - Threading contract documented; _throttle() sleep must not run on main thread
- **scripts/remove_pycache.sh** - Helper script to untrack committed __pycache__ bytecode
"@

gh release create v1.0.6 --title "v1.0.6 - Code Quality & Bug Fix Release" --notes $notes --target main
