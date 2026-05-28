from __future__ import annotations

from threading import RLock
from typing import Final
from uuid import UUID

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus, VideoQuality
from yaloader.domain.source_identity import build_media_source_key
from yaloader.domain.value_objects.media_url import MediaUrl

DOWNLOADABLE_STATUSES: Final[frozenset[DownloadStatus]] = frozenset(
    {
        DownloadStatus.PENDING,
        DownloadStatus.FAILED,
        DownloadStatus.CANCELED,
    }
)


def is_downloadable(task: DownloadTask) -> bool:
    return task.status in DOWNLOADABLE_STATUSES


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

    def remove_task(self, task_id: UUID) -> DownloadTask | None:
        with self._lock:
            task_index = self._task_index_by_id.get(task_id)

            if task_index is None:
                return None

            removed_task = self._tasks.pop(task_index)
            self._rebuild_task_index()

            return removed_task

    def clear_tasks(self) -> int:
        with self._lock:
            removed_count = len(self._tasks)
            self._tasks.clear()
            self._task_index_by_id.clear()

            return removed_count

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

    def apply_metadata(
        self,
        *,
        task_id: UUID,
        title: str | None,
        video_quality: VideoQuality,
    ) -> DownloadTask | None:
        with self._lock:
            task_index = self._task_index_by_id.get(task_id)

            if task_index is None:
                return None

            current_task = self._tasks[task_index]

            if current_task.status is DownloadStatus.RUNNING:
                return current_task

            updated_task = current_task.with_metadata(
                title=title,
                video_quality=video_quality,
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

    def list_downloadable_tasks(self) -> tuple[DownloadTask, ...]:
        with self._lock:
            return tuple(task for task in self._tasks if is_downloadable(task))

    def count(self) -> int:
        with self._lock:
            return len(self._tasks)

    def contains_url(self, url: str) -> bool:
        source_key = build_media_source_key(url=url)

        with self._lock:
            return any(
                build_media_source_key(url=task.url.value) == source_key for task in self._tasks
            )

    def get_task_by_url(self, url: str) -> DownloadTask | None:
        source_key = build_media_source_key(url=url)

        with self._lock:
            for task in self._tasks:
                if build_media_source_key(url=task.url.value) == source_key:
                    return task

        return None

    def _rebuild_task_index(self) -> None:
        self._task_index_by_id = {
            task.task_id: task_index for task_index, task in enumerate(self._tasks)
        }
