"""Update service: checks GitHub Releases API, downloads zip, extracts in-place.

Flow
----
1. GET https://api.github.com/repos/{OWNER}/{REPO}/releases/latest
2. Compare tag_name (e.g. 'v1.2.0') against mlm.__version__.VERSION
3. If newer:  return release metadata dict
   If same/older: return None
4. download_and_install(asset_url, dest_dir) — streams the zip into a temp
   file, then extracts every file, skipping the top-level folder wrapper
   so files land directly in dest_dir (the app root).

All network I/O is intentionally synchronous so it can be driven from a
QThread without any asyncio dependency.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from typing import Callable

OWNER = "faisalabaalkhail70-ux"
REPO  = "media-library-manager"
_API  = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
_UA   = "MediaLibraryManager-Updater/1.0"


def _parse_version(tag: str) -> tuple[int, ...]:
    """'v1.2.3' or '1.2.3' → (1, 2, 3)"""
    clean = tag.lstrip("v").strip()
    try:
        return tuple(int(x) for x in clean.split("."))
    except ValueError:
        return (0,)


def check_for_update() -> dict | None:
    """Return release metadata dict if a newer version exists, else None.

    Raises urllib.error.URLError / OSError on network failure — callers
    should catch and surface as a user-friendly message.
    """
    from mlm.__version__ import VERSION

    req = urllib.request.Request(_API, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())

    latest_tag  = data.get("tag_name", "")
    latest_ver  = _parse_version(latest_tag)
    current_ver = _parse_version(VERSION)

    if latest_ver <= current_ver:
        return None

    # Find the zip asset (prefer the source-code zip GitHub auto-generates)
    zip_url = data.get("zipball_url", "")
    for asset in data.get("assets", []):
        if asset.get("name", "").endswith(".zip"):
            zip_url = asset["browser_download_url"]
            break

    return {
        "tag":      latest_tag,
        "name":     data.get("name") or latest_tag,
        "body":     data.get("body") or "No release notes.",
        "zip_url":  zip_url,
        "html_url": data.get("html_url", ""),
    }


def download_and_install(
    zip_url: str,
    dest_dir: str | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> None:
    """Download *zip_url*, extract it over *dest_dir* (app root by default).

    Parameters
    ----------
    zip_url:     Direct URL to the zip archive.
    dest_dir:    Root folder of the running application.  Defaults to the
                 directory that contains this file's package (two levels up).
    progress_cb: Optional callable(bytes_done, total_bytes).  Called
                 periodically during download so the UI can show a progress bar.
    """
    if dest_dir is None:
        # mlm/services/ → mlm/ → app_root/
        dest_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dest_dir = os.path.dirname(dest_dir)  # go one more level up to project root

    req = urllib.request.Request(zip_url, headers={"User-Agent": _UA})

    # Stream into a temp file
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            done  = 0
            chunk = 65536
            with open(tmp_path, "wb") as f:
                while True:
                    buf = resp.read(chunk)
                    if not buf:
                        break
                    f.write(buf)
                    done += len(buf)
                    if progress_cb:
                        progress_cb(done, total)

        # Extract, stripping the single top-level folder GitHub wraps zips in
        with zipfile.ZipFile(tmp_path, "r") as zf:
            members = zf.infolist()
            # Detect common prefix (e.g. 'repo-v1.2.0/')
            prefix = ""
            if members:
                first = members[0].filename
                if first.endswith("/"):
                    prefix = first

            for member in members:
                rel = member.filename
                if prefix and rel.startswith(prefix):
                    rel = rel[len(prefix):]
                if not rel:          # skip the root dir entry itself
                    continue

                target = os.path.join(dest_dir, rel)
                if member.is_dir():
                    os.makedirs(target, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zf.open(member) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
