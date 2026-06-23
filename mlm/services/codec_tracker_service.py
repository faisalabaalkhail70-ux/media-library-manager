"""R-3 Codec Quality Upgrade Tracker.

Compares current file codec/resolution against the previously recorded
values in the DB (or a provided baseline) and logs codec_upgrade_log
entries when an improvement is detected.

Upgrade detection rules
-----------------------
  Codec quality ranking (higher index = better):
    mpeg2video < mpeg4 < h263 < wmv3 < avc < hevc < av1

  Resolution quality ranking:
    SD (< 720p) < 720p < 1080p < 4K

The service is called from ProbeService after an ffprobe run updates
media_files.  It can also be called manually from the UI for a batch
review.
"""
from __future__ import annotations

import logging
from datetime import datetime

from mlm.db.connection import get_connection

log = logging.getLogger(__name__)

_CODEC_RANK: dict[str, int] = {
    "mpeg2video": 1,
    "h263":       2,
    "mpeg4":      3,
    "wmv3":       4,
    "vc1":        5,
    "avc":        6,
    "h264":       6,   # alias
    "vp8":        7,
    "vp9":        8,
    "hevc":       9,
    "h265":       9,   # alias
    "av1":        10,
}

_RES_RANK: dict[str, int] = {
    "SD":    1,
    "720p":  2,
    "1080p": 3,
    "4K":    4,
}


def _codec_rank(codec: str | None) -> int:
    return _CODEC_RANK.get((codec or "").lower(), 0)


def _res_rank(width: int | None) -> int:
    if not width:
        return 0
    if width >= 3840:
        return _RES_RANK["4K"]
    if width >= 1920:
        return _RES_RANK["1080p"]
    if width >= 1280:
        return _RES_RANK["720p"]
    return _RES_RANK["SD"]


def _res_label(width: int | None) -> str:
    if not width:
        return ""
    if width >= 3840:
        return "4K"
    if width >= 1920:
        return "1080p"
    if width >= 1280:
        return "720p"
    return "SD"


class CodecTrackerService:
    """Detects and logs codec / resolution upgrades."""

    def check_file(self, media_file_id: int) -> dict | None:
        """Compare current probe data against codec_upgrade_log baseline.

        Returns a result dict if an upgrade was detected, else None.
        """
        with get_connection() as conn:
            file_row = conn.execute(
                "SELECT video_codec, width, height FROM media_files WHERE id=?",
                (media_file_id,),
            ).fetchone()
            if not file_row:
                return None

            last_log = conn.execute(
                """
                SELECT new_video_codec, new_resolution
                FROM   codec_upgrade_log
                WHERE  media_file_id=?
                ORDER  BY detected_at DESC
                LIMIT  1
                """,
                (media_file_id,),
            ).fetchone()

        cur_codec = file_row["video_codec"]
        cur_res   = _res_label(file_row["width"])

        if last_log:
            old_codec = last_log["new_video_codec"]
            old_res   = last_log["new_resolution"]
        else:
            # No baseline yet — record current state as baseline
            self._insert_log(
                media_file_id,
                old_codec=None, new_codec=cur_codec,
                old_res=None,   new_res=cur_res,
                upgrade_type="baseline",
            )
            return None

        codec_upgrade = _codec_rank(cur_codec) > _codec_rank(old_codec)
        res_upgrade   = _res_rank(file_row["width"]) > _res_rank(
            3840 if old_res == "4K"
            else 1920 if old_res == "1080p"
            else 1280 if old_res == "720p"
            else 0
        )

        if not codec_upgrade and not res_upgrade:
            return None

        upgrade_type = (
            "both"       if codec_upgrade and res_upgrade
            else "codec" if codec_upgrade
            else "resolution"
        )
        self._insert_log(
            media_file_id,
            old_codec=old_codec, new_codec=cur_codec,
            old_res=old_res,     new_res=cur_res,
            upgrade_type=upgrade_type,
        )
        log.info(
            "[CodecTracker] Upgrade detected for file_id=%d: %s (%s->%s, %s->%s)",
            media_file_id, upgrade_type, old_codec, cur_codec, old_res, cur_res,
        )
        return {
            "media_file_id": media_file_id,
            "upgrade_type":  upgrade_type,
            "old_codec":     old_codec,
            "new_codec":     cur_codec,
            "old_res":       old_res,
            "new_res":       cur_res,
        }

    def batch_check(self, limit: int = 500) -> list[dict]:
        """Check all probed files for upgrades. Returns list of upgrade dicts."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id FROM media_files "
                "WHERE removed_at IS NULL AND video_codec IS NOT NULL "
                "LIMIT ?",
                (limit,),
            ).fetchall()
        results = []
        for r in rows:
            result = self.check_file(r["id"])
            if result:
                results.append(result)
        return results

    def list_upgrades(self, limit: int = 100) -> list[dict]:
        """Return recent codec upgrade log entries."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT cl.*, mf.file_name
                FROM   codec_upgrade_log cl
                JOIN   media_files mf ON mf.id = cl.media_file_id
                WHERE  cl.upgrade_type != 'baseline'
                ORDER  BY cl.detected_at DESC
                LIMIT  ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def _insert_log(
        self,
        media_file_id: int,
        old_codec: str | None,
        new_codec: str | None,
        old_res: str | None,
        new_res: str | None,
        upgrade_type: str,
    ) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO codec_upgrade_log
                    (media_file_id, old_video_codec, new_video_codec,
                     old_resolution, new_resolution, upgrade_type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (media_file_id, old_codec, new_codec, old_res, new_res, upgrade_type),
            )
