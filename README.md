# Atlas — Media Library Manager

A local desktop application for organising, scanning, and managing your personal video collection.
Built with **Python 3.11 · PySide6 · SQLite**. No internet connection required to run — TMDB is used only when you choose to fetch metadata.

---

## What It Does

| Feature | Description |
|---|---|
| **Scanner** | Walks your local folders and discovers video files (`.mkv`, `.mp4`, `.avi`, `.mov`, `.m4v`, `.wmv`, `.ts`, `.webm`, `.flv`, `.vob`) |
| **Library & Movies & Shows** | Browse all discovered files; shows are tracked by season and episode |
| **TMDB Metadata** | Auto-matches files to movies or TV shows using the TMDB API; stores poster, plot, rating, genres |
| **Missing Episodes** | Compares your local files against TMDB season data and highlights what you don't have |
| **Duplicates** | Finds exact duplicates (same size + hash) and possible duplicates (name + duration + size similarity) |
| **Rename** | Bulk rename files using configurable templates: `{Title}`, `{Year}`, `{Season:02}`, `{Episode:02}`, `{Resolution}`, `{Ext}` |
| **Health Check** | Flags 0-byte files, unusually small files, missing-on-disk files, and unprobed files |
| **Reports** | Export your library, missing episodes, or duplicate groups to **CSV**, **Excel**, or **PDF** |
| **Dashboard** | Overview stats: total files, movies, shows, storage size, watch time, top resolutions and codecs |
| **Undo** | Every rename operation is logged in an action ledger and can be reversed |

---

## Requirements

| Requirement | Details |
|---|---|
| Python | 3.11 or newer |
| ffprobe | Part of any standard [ffmpeg](https://ffmpeg.org/download.html) installation; must be on `PATH` |
| TMDB API key | Free — create one at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) |

---

## Installation

```bash
# 1. Clone
git clone https://github.com/faisalabaalkhail70-ux/media-library-manager.git
cd media-library-manager

# 2. Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch
python main.py
```

On first launch the app automatically creates a fresh, empty database and all required folders under `data/`. Nothing needs to be configured in advance.

---

## First-Time Setup (inside the app)

1. **Settings** → enter your TMDB API key and save.
2. **Scanner** → add one or more local media directories and click **Scan**.
3. Once scanning is done, use **Match Metadata** to link files to TMDB entries.
4. Use **Shows → Check Missing Episodes** to compare against TMDB season data.

---

## Data & Privacy

All data is stored **only on your own machine** inside the `data/` folder:

```
data/
├── app.db          ← SQLite database (your library, settings, API key)
├── logs/
│   └── atlas.log   ← Rotating log file (max 5 MB × 3 backups)
└── exports/        ← CSV / Excel / PDF files you generate
```

This folder is listed in `.gitignore` — it is never committed to Git or uploaded anywhere.
Each person who clones the project starts with a completely empty database and enters their own TMDB key.

---

## Rename Templates

The Rename view accepts these tokens:

| Token | Replaced with |
|---|---|
| `{Title}` | Movie or show title from TMDB |
| `{Year}` | Release year |
| `{Season:02}` | Season number, zero-padded |
| `{Episode:02}` | Episode number, zero-padded |
| `{Resolution}` | e.g. `1920x1080` |
| `{Ext}` | File extension including the dot |

Example template: `{Title} ({Year}) S{Season:02}E{Episode:02}{Ext}`

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Project Structure

```
mlm/
├── app/            Bootstrap, config, paths
├── db/             SQLite schema, migrations, repository layer
├── integrations/   TMDB API client, ffprobe client
├── parsing/        Filename parser (title, year, season, episode)
├── services/       Business logic (scan, metadata, health, duplicates, rename, export)
├── ui/
│   ├── views/      One QWidget per sidebar section
│   ├── models/     Qt table models
│   └── styles.py   Global stylesheet
├── utils/          Hashing (MD5), logging, filesystem helpers
└── workers/        QThread background workers (scan, hash, metadata, rename, undo)
data/               Auto-created on first run — not in Git
tests/              pytest test suite
main.py             Entry point
```
