"""R-6 Library Snapshot / Diff.

A snapshot is a point-in-time frozen record of every media file's
path, size, entity title, health status, and codec.  Diffing two
snapshots reveals exactly what was added, removed, or changed.

Usage
-----
    svc = SnapshotService()
    snap_id = svc.take_snapshot(label='before upgrade')
    ...  # do work
    diff   = svc.diff(snap_id, latest=True)
    report = svc.format_diff_report(diff)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from mlm.db.connection import get_connection

log = logging.getLogger(__name__)


@dataclass
class SnapshotDiff:
    snap_a_id:    int
    snap_b_id:    int
    snap_a_label: str
    snap_b_label: str
    added:        list[dict] = field(default_factory=list)   # in B not A
    removed:      list[dict] = field(default_factory=list)   # in A not B
    changed:      list[dict] = field(default_factory=list)   # same path, different attrs
    unchanged:    int        = 0


class SnapshotService:
    """Take, list, diff, and delete library snapshots."""

    # ------------------------------------------------------------------
    # Taking a snapshot
    # ------------------------------------------------------------------

    def take_snapshot(self, label: str = "") -> int:
        """Freeze the current library state. Returns the new snapshot_id."""
        now = datetime.utcnow().isoformat()
        with get_connection() as conn:
            # Collect live file rows
            rows = conn.execute(
                """
                SELECT
                    mf.id,
                    mf.file_path,
                    mf.file_size_bytes,
                    mf.health_status,
                    mf.video_codec,
                    COALESCE(e.title, '') AS entity_title
                FROM  media_files mf
                LEFT  JOIN media_entities e ON e.id = mf.entity_id
                WHERE mf.removed_at IS NULL
                """
            ).fetchall()

            total_bytes = sum(r["file_size_bytes"] for r in rows)

            # Insert snapshot header
            cur = conn.execute(
                "INSERT INTO library_snapshots (label, taken_at, file_count, total_bytes) "
                "VALUES (?, ?, ?, ?)",
                (label or now[:10], now, len(rows), total_bytes),
            )
            snap_id = cur.lastrowid

            # Bulk-insert snapshot rows
            conn.executemany(
                """
                INSERT INTO snapshot_files
                    (snapshot_id, media_file_id, file_path, file_size_bytes,
                     entity_title, health_status, video_codec)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        snap_id,
                        r["id"],
                        r["file_path"],
                        r["file_size_bytes"],
                        r["entity_title"],
                        r["health_status"],
                        r["video_codec"],
                    )
                    for r in rows
                ],
            )

        log.info(
            "[Snapshot] Took snapshot #%d '%s' — %d files, %.1f GB",
            snap_id, label, len(rows), total_bytes / 1024 ** 3,
        )
        return snap_id

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_snapshots(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM library_snapshots ORDER BY taken_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_snapshot_files(self, snap_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM snapshot_files WHERE snapshot_id=? ORDER BY file_path",
                (snap_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Diffing
    # ------------------------------------------------------------------

    def diff(
        self,
        snap_a_id: int,
        snap_b_id: int | None = None,
        latest: bool = False,
    ) -> SnapshotDiff:
        """Diff snapshot A against snapshot B (or the latest if *latest=True*)."""
        if latest or snap_b_id is None:
            snaps = self.list_snapshots()
            if not snaps:
                raise ValueError("No snapshots available to diff against.")
            snap_b_id = snaps[0]["id"]   # most recent

        files_a = {r["file_path"]: r for r in self.get_snapshot_files(snap_a_id)}
        files_b = {r["file_path"]: r for r in self.get_snapshot_files(snap_b_id)}

        snap_a_meta = self._meta(snap_a_id)
        snap_b_meta = self._meta(snap_b_id)

        added   = [files_b[p] for p in files_b if p not in files_a]
        removed = [files_a[p] for p in files_a if p not in files_b]
        changed = []
        unchanged = 0

        for path, row_a in files_a.items():
            if path not in files_b:
                continue
            row_b = files_b[path]
            diffs: dict = {}
            for key in ("file_size_bytes", "health_status", "video_codec", "entity_title"):
                va, vb = row_a.get(key), row_b.get(key)
                if va != vb:
                    diffs[key] = {"before": va, "after": vb}
            if diffs:
                changed.append({"file_path": path, "changes": diffs})
            else:
                unchanged += 1

        return SnapshotDiff(
            snap_a_id    = snap_a_id,
            snap_b_id    = snap_b_id,
            snap_a_label = snap_a_meta.get("label", ""),
            snap_b_label = snap_b_meta.get("label", ""),
            added        = added,
            removed      = removed,
            changed      = changed,
            unchanged    = unchanged,
        )

    def format_diff_report(self, diff: SnapshotDiff) -> str:
        """Return a human-readable plain-text diff summary."""
        lines = [
            f"Library Diff: '{diff.snap_a_label}' → '{diff.snap_b_label}'",
            f"  + Added:    {len(diff.added)}",
            f"  - Removed:  {len(diff.removed)}",
            f"  ~ Changed:  {len(diff.changed)}",
            f"  = Unchanged:{diff.unchanged}",
            "",
        ]
        if diff.added:
            lines.append("ADDED:")
            for r in diff.added[:50]:
                lines.append(f"  + {r['file_path']}")
        if diff.removed:
            lines.append("REMOVED:")
            for r in diff.removed[:50]:
                lines.append(f"  - {r['file_path']}")
        if diff.changed:
            lines.append("CHANGED:")
            for r in diff.changed[:50]:
                lines.append(f"  ~ {r['file_path']}")
                for k, v in r["changes"].items():
                    lines.append(f"      {k}: {v['before']} -> {v['after']}")
        return "\n".join(lines)

    # ------------------------------------------------------------------

    def delete_snapshot(self, snap_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM library_snapshots WHERE id=?", (snap_id,)
            )  # cascade deletes snapshot_files via FK

    def _meta(self, snap_id: int) -> dict:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM library_snapshots WHERE id=?", (snap_id,)
            ).fetchone()
        return dict(row) if row else {}
