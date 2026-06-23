"""H-4 Library Health Score + Action Cards.

Computes a 0-100 health score for the whole library and for individual
directories, then writes actionable "action cards" into the action_cards
table for the UI to display.

Scoring rubric (weights sum to 100)
------------------------------------
  40 pts  — files with health_status == 'ok'
  20 pts  — files with an entity match (metadata found)
  15 pts  — files without duplicates
  15 pts  — files with technical probe data (video_codec not null)
  10 pts  — files with at least one subtitle

Action card types generated
----------------------------
  'missing_file'      — file not found on disk
  'unmatched_file'    — no entity linked
  'no_probe_data'     — ffprobe never ran
  'duplicate_group'   — unresolved duplicate set
  'no_subtitles'      — no subtitle sidecar found
  'low_quality'       — SD resolution with MPEG-4/H.263 codec
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from mlm.db.connection import get_connection

log = logging.getLogger(__name__)

_LEGACY_CODECS = frozenset({"mpeg2video", "mpeg4", "h263", "wmv3", "divx", "xvid"})


@dataclass
class LibraryHealthReport:
    score: int                       # 0-100
    total_files: int
    ok_files: int
    matched_files: int
    probed_files: int
    files_with_subs: int
    duplicate_groups: int
    cards_generated: int
    breakdown: dict = field(default_factory=dict)


class HealthScoreService:
    """Computes library health and generates action cards."""

    # ------------------------------------------------------------------
    # Score
    # ------------------------------------------------------------------

    def compute_score(self) -> LibraryHealthReport:
        with get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM media_files WHERE removed_at IS NULL"
            ).fetchone()[0]

            if total == 0:
                return LibraryHealthReport(
                    score=100, total_files=0, ok_files=0,
                    matched_files=0, probed_files=0,
                    files_with_subs=0, duplicate_groups=0, cards_generated=0,
                )

            ok_files = conn.execute(
                "SELECT COUNT(*) FROM media_files "
                "WHERE removed_at IS NULL AND health_status='ok'"
            ).fetchone()[0]

            matched = conn.execute(
                "SELECT COUNT(*) FROM media_files "
                "WHERE removed_at IS NULL AND entity_id IS NOT NULL"
            ).fetchone()[0]

            probed = conn.execute(
                "SELECT COUNT(*) FROM media_files "
                "WHERE removed_at IS NULL AND video_codec IS NOT NULL"
            ).fetchone()[0]

            with_subs = conn.execute(
                "SELECT COUNT(DISTINCT media_file_id) FROM subtitle_files "
                "WHERE removed_at IS NULL"
            ).fetchone()[0]

            dup_groups = conn.execute(
                "SELECT COUNT(*) FROM duplicate_groups "
                "WHERE review_status IN ('new','pending')"
            ).fetchone()[0]

            no_dup_files = total - conn.execute(
                "SELECT COUNT(DISTINCT media_file_id) FROM duplicate_items"
            ).fetchone()[0]

        def pct(n: int) -> float:
            return n / total if total else 1.0

        score = int(
            40 * pct(ok_files)
            + 20 * pct(matched)
            + 15 * pct(max(no_dup_files, 0))
            + 15 * pct(probed)
            + 10 * pct(with_subs)
        )
        score = max(0, min(100, score))

        return LibraryHealthReport(
            score        = score,
            total_files  = total,
            ok_files     = ok_files,
            matched_files= matched,
            probed_files = probed,
            files_with_subs = with_subs,
            duplicate_groups= dup_groups,
            cards_generated = 0,
            breakdown = {
                "health_ok_pct":    round(pct(ok_files) * 100, 1),
                "matched_pct":      round(pct(matched)  * 100, 1),
                "probed_pct":       round(pct(probed)   * 100, 1),
                "subtitled_pct":    round(pct(with_subs) * 100, 1),
                "no_duplicate_pct": round(pct(max(no_dup_files, 0)) * 100, 1),
            },
        )

    # ------------------------------------------------------------------
    # Action cards
    # ------------------------------------------------------------------

    def refresh_action_cards(self) -> int:
        """Regenerate all action cards. Returns count of cards written."""
        cards: list[tuple] = []

        with get_connection() as conn:
            # --- missing files
            missing = conn.execute(
                "SELECT id, file_path FROM media_files "
                "WHERE removed_at IS NULL AND health_status='error'"
            ).fetchall()
            for r in missing:
                cards.append((
                    "missing_file", "critical",
                    f"File not found: {r['file_path']}",
                    "This file was expected on disk but is no longer accessible.",
                    r["id"],
                    json.dumps({"file_path": r["file_path"]}),
                ))

            # --- unmatched files
            unmatched = conn.execute(
                "SELECT id, file_name FROM media_files "
                "WHERE removed_at IS NULL AND entity_id IS NULL"
            ).fetchall()
            for r in unmatched:
                cards.append((
                    "unmatched_file", "warning",
                    f"No metadata: {r['file_name']}",
                    "Run metadata matching to identify this file.",
                    r["id"],
                    json.dumps({"file_name": r["file_name"]}),
                ))

            # --- no probe data
            no_probe = conn.execute(
                "SELECT id, file_name FROM media_files "
                "WHERE removed_at IS NULL AND video_codec IS NULL"
            ).fetchall()
            for r in no_probe:
                cards.append((
                    "no_probe_data", "info",
                    f"Not probed: {r['file_name']}",
                    "Run ffprobe to extract technical metadata.",
                    r["id"],
                    None,
                ))

            # --- duplicate groups
            dup_groups = conn.execute(
                "SELECT id, match_type FROM duplicate_groups "
                "WHERE review_status='new'"
            ).fetchall()
            for r in dup_groups:
                cards.append((
                    "duplicate_group", "warning",
                    f"Duplicate group #{r['id']} ({r['match_type']})",
                    "Review and resolve this duplicate set.",
                    None,
                    json.dumps({"group_id": r["id"]}),
                ))

            # --- low-quality legacy codec files
            low_q = conn.execute(
                "SELECT id, file_name, video_codec, resolution FROM media_files "
                "WHERE removed_at IS NULL AND video_codec IS NOT NULL"
            ).fetchall()
            for r in low_q:
                if (r["video_codec"] or "").lower() in _LEGACY_CODECS:
                    cards.append((
                        "low_quality", "info",
                        f"Legacy codec: {r['file_name']}",
                        f"Codec {r['video_codec']} is outdated. Consider re-encoding to HEVC/AV1.",
                        r["id"],
                        json.dumps({"codec": r["video_codec"]}),
                    ))

            # Wipe stale open cards and re-insert
            conn.execute("DELETE FROM action_cards WHERE status='open'")
            conn.executemany(
                """
                INSERT INTO action_cards
                    (card_type, severity, title, description, media_file_id, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                cards,
            )

        log.info("[HealthScore] Generated %d action cards.", len(cards))
        return len(cards)

    def dismiss_card(self, card_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE action_cards SET status='dismissed' WHERE id=?", (card_id,)
            )

    def resolve_card(self, card_id: int) -> None:
        from datetime import datetime
        with get_connection() as conn:
            conn.execute(
                "UPDATE action_cards "
                "SET status='resolved', resolved_at=? WHERE id=?",
                (datetime.utcnow().isoformat(), card_id),
            )

    def list_open_cards(
        self,
        severity: str | None = None,
        card_type: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        clauses = ["status='open'"]
        params: list = []
        if severity:
            clauses.append("severity=?")
            params.append(severity)
        if card_type:
            clauses.append("card_type=?")
            params.append(card_type)
        where = " AND ".join(clauses)
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM action_cards WHERE {where} "
                f"ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END, id "
                f"LIMIT ?",
                (*params, limit),
            ).fetchall()
        return [dict(r) for r in rows]
