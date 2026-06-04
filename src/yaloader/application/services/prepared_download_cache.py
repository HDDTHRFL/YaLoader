from __future__ import annotations

from threading import RLock
from uuid import UUID

from yaloader.application.dto.prepared_download import PreparedDownload


class PreparedDownloadCache:
    def __init__(self) -> None:
        self._lock = RLock()
        self._prepared_downloads_by_task_id: dict[UUID, PreparedDownload] = {}

    def save(self, *, prepared_download: PreparedDownload) -> None:
        with self._lock:
            self._prepared_downloads_by_task_id[prepared_download.task_id] = prepared_download

    def get(self, *, task_id: UUID) -> PreparedDownload | None:
        with self._lock:
            return self._prepared_downloads_by_task_id.get(task_id)

    def contains(self, *, task_id: UUID) -> bool:
        with self._lock:
            return task_id in self._prepared_downloads_by_task_id

    def remove(self, *, task_id: UUID) -> PreparedDownload | None:
        with self._lock:
            return self._prepared_downloads_by_task_id.pop(task_id, None)

    def clear(self) -> int:
        with self._lock:
            removed_count = len(self._prepared_downloads_by_task_id)
            self._prepared_downloads_by_task_id.clear()

            return removed_count

    def count(self) -> int:
        with self._lock:
            return len(self._prepared_downloads_by_task_id)
