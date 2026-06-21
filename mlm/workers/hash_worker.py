from PySide6.QtCore import QThread, Signal
from mlm.db.repositories.files_repo import FilesRepository
from mlm.utils.hashing import partial_md5, full_md5


class HashWorker(QThread):
    progress  = Signal(int, int)   # (done, total)
    finished  = Signal(int)        # files_hashed
    failed    = Signal(str)

    def __init__(self, mode: str = "partial") -> None:
        """
        mode = "partial"  → حساب partial hash فقط (سريع)
        mode = "full"     → حساب full hash للملفات التي لها نفس partial hash
        """
        super().__init__()
        self.mode = mode
        self.repo = FilesRepository()
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        try:
            files = self._get_unhashed_files()
            total = len(files)
            done  = 0

            for row in files:
                if not self._running:
                    break

                path = row["file_path"]
                try:
                    if self.mode == "full":
                        h = full_md5(path)
                        self.repo.save_hashes(file_path=path, full_hash=h)
                    else:
                        h = partial_md5(path)
                        self.repo.save_hashes(file_path=path, partial_hash=h)
                except (OSError, PermissionError):
                    pass  # ملف تالف أو محذوف — تجاوز

                done += 1
                if done % 5 == 0:
                    self.progress.emit(done, total)

            self.finished.emit(done)

        except Exception as exc:
            self.failed.emit(str(exc))

    def _get_unhashed_files(self) -> list[dict]:
        from mlm.db.connection import get_connection
        col = "partial_hash" if self.mode == "partial" else "full_hash"
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT id, file_path, file_size_bytes
                FROM media_files
                WHERE removed_at IS NULL
                  AND {col} IS NULL
                ORDER BY file_size_bytes DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]