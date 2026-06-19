from pathlib import Path
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from mlm.app.paths import EXPORT_DIR
from mlm.db.connection import create_connection

class ExportService:
    def __init__(self) -> None:
        self.conn = create_connection()
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    def _query_dataframe(self, report_name: str) -> pd.DataFrame:
        queries = {
            "library": """
                SELECT mf.file_name, mf.file_path, mf.file_size_bytes, mf.resolution,
                       mf.video_codec, mf.duration_seconds, mf.health_status,
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
                SELECT dg.match_type, dg.confidence, mf.file_name, mf.file_path,
                       mf.file_size_bytes, mf.resolution, mf.video_codec
                FROM duplicate_items di
                JOIN duplicate_groups dg ON dg.id = di.group_id
                JOIN media_files mf ON mf.id = di.media_file_id
                ORDER BY dg.id, mf.file_name
            """,
        }
        return pd.read_sql_query(queries[report_name], self.conn)

    def export_csv(self, report_name: str) -> str:
        df = self._query_dataframe(report_name)
        out = EXPORT_DIR / f"{report_name}.csv"
        df.to_csv(out, index=False)
        return str(out)

    def export_excel(self, report_name: str) -> str:
        df = self._query_dataframe(report_name)
        out = EXPORT_DIR / f"{report_name}.xlsx"
        df.to_excel(out, index=False)
        return str(out)

    def export_pdf(self, report_name: str) -> str:
        df = self._query_dataframe(report_name)
        out = EXPORT_DIR / f"{report_name}.pdf"

        c = canvas.Canvas(str(out), pagesize=A4)
        width, height = A4
        y = height - 40

        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, f"Media Library Manager Report: {report_name}")
        y -= 30

        c.setFont("Helvetica", 9)
        for _, row in df.head(40).iterrows():
            line = " | ".join(str(v)[:30] for v in row.tolist())
            c.drawString(40, y, line[:140])
            y -= 14
            if y < 50:
                c.showPage()
                y = height - 40
                c.setFont("Helvetica", 9)

        c.save()
        return str(out)