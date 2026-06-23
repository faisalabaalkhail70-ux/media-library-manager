"""Background worker that exports a report to CSV, Excel, or PDF."""
import logging

from PySide6.QtCore import Signal

from mlm.services.export_service import ExportService
from mlm.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)


class ExportWorker(BaseWorker):
    """Run an export job in the background."""

    finished_export = Signal(str, str, str)

    def __init__(self, report_name: str, export_format: str) -> None:
        super().__init__()
        self.report_name = report_name
        self.export_format = export_format
        self.service = ExportService()

    def _execute(self) -> None:
        fmt = self.export_format
        if fmt == "csv":
            out = self.service.export_csv(self.report_name)
        elif fmt == "excel":
            out = self.service.export_excel(self.report_name)
        elif fmt == "pdf":
            out = self.service.export_pdf(self.report_name)
        else:
            raise RuntimeError(f"Unsupported export format: {fmt!r}")
        self.finished_export.emit(self.report_name, fmt, out)
