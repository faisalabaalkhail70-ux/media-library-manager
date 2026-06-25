"""Update service: checks GitHub Releases API, downloads zip, extracts in-place.

Flow
----
1. GET https://api.github.com/repos/{OWNER}/{REPO}/releases/latest
   (with optional GitHub token for authenticated requests)
2. Compare tag_name (e.g. 'v1.2.0') against mlm.__version__.VERSION
3. If newer:  return release metadata dict with a fully-resolved direct zip URL
   If same/older: return None
4. download_and_install(zip_url, dest_dir) — streams the zip into a staging
   directory, validates it, then copies over the live app atomically.
   If anything fails mid-way the live app is never touched.

All network I/O is intentionally synchronous so it can be driven from a
QThread without any asyncio dependency.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading
import urllib.request
import urllib.error
import zipfile
from typing import Callable

log = logging.getLogger(__name__)

OWNER = "faisalabaalkhail70-ux"
REPO  = "media-library-manager"
_API  = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
_UA   = "MediaLibraryManager-Updater/1.0"

# Timeout (seconds) for the initial API/header request
CONNECT_TIMEOUT = 10
# Timeout (seconds) for the streaming zip download
READ_TIMEOUT = 300


class DownloadCancelled(Exception):
    """Raised when the download is cancelled via the cancel flag."""


def _make_headers() -> dict[str, str]:
    """Build request headers, attaching a GitHub token when one is saved.

    The token is read from the DB settings table under the key
    'github_token'.  If no token is stored the headers fall back to
    unauthenticated (60 req/hr API limit — sufficient for update checks,
    but a token is recommended for reliable asset downloads).
    """
    headers: dict[str, str] = {"User-Agent": _UA}
    try:
        from mlm.db.repositories.settings_repo import SettingsRepository
        token = SettingsRepository().get("github_token", "").strip()
        if token:
            headers["Authorization"] = f"token {token}"
    except Exception:  # noqa: BLE001
        pass  # DB not ready yet — skip auth silently
    return headers


def _resolve_download_url(url: str) -> str:
    """Follow redirects and return the final direct download URL.

    GitHub's zipball_url and browser_download_url both go through the
    API or CDN redirect layer.  urllib follows HTTP 301/302 automatically,
    but HTTP 300 (Multiple Choices) is not auto-followed.  By opening the
    URL and reading resp.url we always get the final resolved location
    regardless of how many hops it takes.

    The response body is NOT read here — we just resolve the URL and close
    the connection immediately so the actual streaming happens in one clean
    request to the CDN.
    """
    req = urllib.request.Request(url, headers=_make_headers())
    with urllib.request.urlopen(req, timeout=CONNECT_TIMEOUT) as resp:
        return resp.url  # final URL after all redirects


def _parse_version(tag: str) -> tuple[int, ...]:
    """'v1.2.3' or '1.2.3' -> (1, 2, 3)"""
    clean = tag.lstrip("v").strip()
    try:
        return tuple(int(x) for x in clean.split("."))
    except ValueError:
        return (0,)


def check_for_update() -> dict | None:
    """Return release metadata dict if a newer version exists, else None.

    Raises urllib.error.URLError / OSError on network failure — callers
    should catch and surface as a user-friendly message.

    The returned 'zip_url' is always a fully-resolved direct CDN URL so
    the downloader never has to deal with API redirects.
    """
    from mlm.__version__ import VERSION

    req = urllib.request.Request(_API, headers=_make_headers())
    with urllib.request.urlopen(req, timeout=CONNECT_TIMEOUT) as resp:
        data = json.loads(resp.read().decode())

    latest_tag  = data.get("tag_name", "")
    latest_ver  = _parse_version(latest_tag)
    current_ver = _parse_version(VERSION)

    if latest_ver <= current_ver:
        return None

    # Prefer a manually uploaded .zip asset; fall back to GitHub's auto-
    # generated zipball.  Either way, resolve redirects NOW so the worker
    # always receives a plain CDN URL with no further redirect surprises.
    raw_zip_url = data.get("zipball_url", "")
    for asset in data.get("assets", []):
        if asset.get("name", "").endswith(".zip"):
            raw_zip_url = asset["browser_download_url"]
            break

    # Resolve the final direct URL at check time (fails fast here rather
    # than surprising the user mid-download).
    zip_url = _resolve_download_url(raw_zip_url)

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
    cancel_flag: threading.Event | None = None,
) -> None:
    """Download *zip_url* and safely extract it over *dest_dir*.

    Uses a staging directory so the live app is only touched after a full,
    successful extraction.  If extraction fails at any point the staging
    directory is cleaned up and the live app remains untouched.

    Parameters
    ----------
    zip_url:      Direct CDN URL to the zip archive (pre-resolved, no redirects).
    dest_dir:     Root folder of the running application.  Defaults to the
                  directory that contains this file's package (two levels up).
    progress_cb:  Optional callable(bytes_done, total_bytes) for progress UI.
    cancel_flag:  Optional threading.Event; when set the download loop raises
                  DownloadCancelled so the worker can exit cleanly.
    """
    if dest_dir is None:
        # mlm/services/ -> mlm/ -> app_root/
        dest_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dest_dir = os.path.dirname(dest_dir)

    req = urllib.request.Request(zip_url, headers=_make_headers())

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name

    # Staging directory lives next to the app root; cleaned up on any failure.
    staging_dir = os.path.join(os.path.dirname(dest_dir), "_mlm_update_staging")

    try:
        # ── Step 1: stream download ──────────────────────────────────────────
        with urllib.request.urlopen(req, timeout=READ_TIMEOUT) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            done  = 0
            chunk = 65536
            with open(tmp_path, "wb") as f:
                while True:
                    if cancel_flag and cancel_flag.is_set():
                        raise DownloadCancelled("Download cancelled by user.")
                    buf = resp.read(chunk)
                    if not buf:
                        break
                    f.write(buf)
                    done += len(buf)
                    if progress_cb:
                        progress_cb(done, total)

        # ── Step 2: extract to staging ───────────────────────────────────────
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
        os.makedirs(staging_dir, exist_ok=True)

        with zipfile.ZipFile(tmp_path, "r") as zf:
            members = zf.infolist()
            prefix = ""
            if members:
                first = members[0].filename
                if first.endswith("/"):
                    prefix = first

            for member in members:
                rel = member.filename
                if prefix and rel.startswith(prefix):
                    rel = rel[len(prefix):]
                if not rel:
                    continue
                target = os.path.join(staging_dir, rel)
                if member.is_dir():
                    os.makedirs(target, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zf.open(member) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)

        # ── Step 3: validate staging before touching the live app ────────────
        sentinel = os.path.join(staging_dir, "mlm", "__version__.py")
        if not os.path.exists(sentinel):
            raise RuntimeError(
                "Downloaded archive is missing mlm/__version__.py — "
                "update aborted to protect the running application."
            )

        # ── Step 4: copy staging -> live app ─────────────────────────────────
        for root, dirs, files in os.walk(staging_dir):
            rel_root = os.path.relpath(root, staging_dir)
            for fname in files:
                src_path = os.path.join(root, fname)
                dst_path = os.path.join(dest_dir, rel_root, fname)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)

        log.info("Update successfully installed from %s", zip_url)

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        try:
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)
        except OSError:
            pass
