from PySide6.QtCore import QThread, Signal
from mlm.services.export_service import ExportService


class ExportWorker(QThread):
    finished_export = Signal(str, str, str)
    failed = Signal(str)

    def __init__(self, report_name: str, export_format: str) -> None:
        super().__init__()
        self.report_name = report_name
        self.export_format = export_format
        self.service = ExportService()

    def run(self) -> None:
        try:
            if self.export_format == "csv":
                out = self.service.export_csv(self.report_name)
            elif self.export_format == "excel":
                out = self.service.export_excel(self.report_name)
            elif self.export_format == "pdf":
                out = self.service.export_pdf(self.report_name)
            else:
                raise RuntimeError(f"Unsupported export format: {self.export_format}")

            self.finished_export.emit(self.report_name, self.export_format, out)
        except Exception as exc:
            self.failed.emit(str(exc))