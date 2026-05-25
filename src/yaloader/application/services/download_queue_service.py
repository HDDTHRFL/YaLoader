from __future__ import annotations

from threading import RLock
from uuid import UUID

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus
from yaloader.domain.value_objects.media_url import MediaUrl


class DownloadQueueService:
    def __init__(self) -> None:
        self._lock = RLock()
        self._tasks: list[DownloadTask] = []
        self._task_index_by_id: dict[UUID, int] = {}

    def add_download(self, request: DownloadRequest) -> DownloadTask:
        task = DownloadTask.create(
            url=MediaUrl(value=request.url),
            target_dir=request.target_dir,
            mode=request.mode,
            output_format=request.output_format,
            video_quality=request.video_quality,
            include_playlist=request.include_playlist,
        )

        with self._lock:
            self._task_index_by_id[task.task_id] = len(self._tasks)
            self._tasks.append(task)

        return task

    def get_task(self, task_id: UUID) -> DownloadTask | None:
        with self._lock:
            task_index = self._task_index_by_id.get(task_id)

            if task_index is None:
                return None

            return self._tasks[task_index]

    def update_status(
        self,
        *,
        task_id: UUID,
        status: DownloadStatus,
        error_message: str | None = None,
    ) -> DownloadTask | None:
        with self._lock:
            task_index = self._task_index_by_id.get(task_id)

            if task_index is None:
                return None

            updated_task = self._tasks[task_index].with_status(
                status=status,
                error_message=error_message,
            )
            self._tasks[task_index] = updated_task

            return updated_task

    def apply_result(self, result: DownloadResult) -> DownloadTask | None:
        return self.update_status(
            task_id=result.task_id,
            status=result.status,
            error_message=result.error_message,
        )

    def list_tasks(self) -> tuple[DownloadTask, ...]:
        with self._lock:
            return tuple(self._tasks)

    def count(self) -> int:
        with self._lock:
            return len(self._tasks)
