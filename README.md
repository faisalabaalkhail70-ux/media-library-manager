# Atlas — Media Library Manager

A desktop application for managing local video libraries. Built with **Python + PySide6 + SQLite**.

> **Privacy notice:** The `data/` folder is intentionally excluded from version control via `.gitignore`. It is created automatically on first launch and stores only local data on your own device — nothing is shared or uploaded.

---

## Features

- Scan local directories for video files (`.mkv`, `.mp4`, `.avi`, `.m4v`, `.mov`, `.wmv`, `.ts`, `.webm`, `.flv`, `.vob`)
- Auto-match movies and TV shows via the [TMDB API](https://www.themoviedb.org/)
- Probe video metadata using `ffprobe`
- Detect exact and fuzzy duplicate files
- Bulk rename with template patterns (`{Title}`, `{Year}`, `{Season:02}`, `{Episode:02}`)
- Health-check your library for missing or corrupt files
- Export reports to CSV, Excel, or PDF
- Full undo ledger for all file operations

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| ffprobe | Any recent ffmpeg build |
| TMDB API key | Free at [themoviedb.org](https://www.themoviedb.org/settings/api) |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/faisalabaalkhail70-ux/media-library-manager.git
cd media-library-manager

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python main.py
```

On first launch Atlas will automatically:
- Create the `data/` folder
- Initialise a fresh, empty `data/app.db` SQLite database
- Create `data/logs/` and `data/exports/` directories

**No configuration file is needed.** The database is created from scratch for every new user.

---

## First-Time Setup (inside the app)

1. Open **Settings** and paste your TMDB API key.
2. Go to **Directories** and add your media folders.
3. Click **Scan** to discover your files.
4. Use **Match Metadata** to link files to TMDB entries.

---

## Data Storage — Privacy by Design

All data Atlas stores lives exclusively in the `data/` folder **on your local machine**:

| Path | Contents |
|---|---|
| `data/app.db` | SQLite database (your media library, settings, API key) |
| `data/logs/atlas.log` | Rotating application log |
| `data/exports/` | CSV / Excel / PDF exports you generate |

This folder is listed in `.gitignore` and will **never** be committed to or shared via Git. Each person who downloads the project starts with a completely empty database.

---

## TMDB API Key — Security Notes

- Your API key is stored inside `data/app.db` — a local file that only you can access.
- It is sent to TMDB using an `Authorization: Bearer` header and is **never** written to URLs, logs, or any file outside `data/`.
- If you believe your key has been exposed, revoke it immediately at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) and generate a new one.

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
├── app/          # Bootstrap, config, paths
├── db/           # SQLite schema + repository layer
├── domain/       # Domain models
├── integrations/ # TMDB API client, ffprobe client
├── parsing/      # Media filename parser
├── services/     # Business logic
├── ui/           # PySide6 views and widgets
├── utils/        # Hashing, logging, filesystem helpers
└── workers/      # QThread background workers
data/             # AUTO-CREATED on first run — not in Git
tests/            # pytest test suite
main.py           # Entry point
```

---

## License

MIT
