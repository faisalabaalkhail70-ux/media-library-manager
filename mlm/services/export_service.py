"""Export service — CSV, JSON, Excel, PDF with timestamped filenames."""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from mlm.app.paths import EXPORT_DIR
from mlm.db.connection import get_connection


REPORT_QUERIES: dict[str, str] = {
    "library": """
        SELECT mf.file_name, mf.file_path, mf.file_size_bytes,
               mf.resolution, mf.video_codec, mf.duration_seconds,
               mf.health_status,
               me.media_type, me.title AS matched_title, me.release_year
        FROM media_files mf
        LEFT JOIN media_entities me ON me.id = mf.entity_id
        WHERE mf.removed_at IS NULL
        ORDER BY mf.file_name
    """,
    "missing_episodes": """
        SELECT me.title AS show_title, ep.season_number, ep.episode_number,
               ep.episode_title, ep.air_date
        FROM episodes ep
        JOIN media_entities me ON me.id = ep.entity_id
        WHERE ep.is_missing = 1
        ORDER BY me.title, ep.season_number, ep.episode_number
    """,
    "duplicates": """
        SELECT dg.match_type, dg.confidence,
               mf.file_name, mf.file_path,
               mf.file_size_bytes, mf.resolution, mf.video_codec
        FROM duplicate_items di
        JOIN duplicate_groups dg ON dg.id = di.group_id
        JOIN media_files mf      ON mf.id = di.media_file_id
        ORDER BY dg.id, mf.file_name
    """,
    "watchlist": """
        SELECT me.title, me.media_type, me.release_year, me.rating,
               w.priority, w.notes, w.added_at, w.watched_at
        FROM watchlist w
        JOIN media_entities me ON me.id = w.entity_id
        ORDER BY w.priority, me.title
    """,
}

_MAX_CELL = 22  # max chars per PDF cell before truncation


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class ExportService:
    def __init__(self) -> None:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    def _query_dataframe(self, report_name: str) -> pd.DataFrame:
        query = REPORT_QUERIES.get(report_name)
        if not query:
            raise ValueError(f"Unknown report: {report_name}")
        with get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def export_csv(self, report_name: str) -> str:
        df = self._query_dataframe(report_name)
        out = EXPORT_DIR / f"{report_name}_{_timestamp()}.csv"
        df.to_csv(out, index=False)
        return str(out)

    def export_json(self, report_name: str) -> str:
        """Export as pretty-printed JSON array."""
        df = self._query_dataframe(report_name)
        out = EXPORT_DIR / f"{report_name}_{_timestamp()}.json"
        out.write_text(
            json.dumps(df.to_dict(orient="records"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(out)

    def export_excel(self, report_name: str) -> str:
        df = self._query_dataframe(report_name)
        out = EXPORT_DIR / f"{report_name}_{_timestamp()}.xlsx"
        df.to_excel(out, index=False)
        return str(out)

    def export_pdf(self, report_name: str) -> str:
        """Generate a paginated PDF using reportlab Platypus.

        Previously used ``df.iterrows()`` which is the slowest possible way
        to iterate a DataFrame (Python object per cell).  Now uses a list
        comprehension over ``df.itertuples()`` (2-5x faster) and delegates
        layout to a Platypus ``Table`` so reportlab handles page breaks,
        column widths, and header repetition automatically.
        """
        df = self._query_dataframe(report_name)
        out = EXPORT_DIR / f"{report_name}_{_timestamp()}.pdf"

        styles = getSampleStyleSheet()
        title_text = report_name.replace("_", " ").title()

        # Build table data as a plain list-of-lists — no Python row loop.
        headers = [str(c)[:_MAX_CELL] for c in df.columns]
        data_rows = [
            [str(v)[:_MAX_CELL] for v in row]
            for row in df.itertuples(index=False)
        ]
        table_data = [headers] + data_rows

        tbl = Table(table_data, repeatRows=1, hAlign="LEFT")
        tbl.setStyle(
            TableStyle(
                [
                    # Header row
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    # Alternating row colours
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f5f5f5")],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )

        doc = SimpleDocTemplate(
            str(out),
            pagesize=A4,
            leftMargin=30,
            rightMargin=30,
            topMargin=40,
            bottomMargin=30,
        )
        doc.build(
            [
                Paragraph(
                    f"Media Library Manager \u2014 {title_text}",
                    styles["Title"],
                ),
                Spacer(1, 12),
                tbl,
            ]
        )
        return str(out)
