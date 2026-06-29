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

SPEED_LIMIT_MUTABLE_STATUSES: Final[frozenset[DownloadStatus]] = frozenset(
    {
        DownloadStatus.PENDING,
        DownloadStatus.RUNNING,
        DownloadStatus.FAILED,
        DownloadStatus.CANCELED,
    }
)


def is_downloadable(task: DownloadTask) -> bool:
    return task.status in DOWNLOADABLE_STATUSES


def can_update_download_speed_limit(task: DownloadTask) -> bool:
    return task.status in SPEED_LIMIT_MUTABLE_STATUSES


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
            separate_audio_video_enabled=request.separate_audio_video_enabled,
            separate_audio_format=request.separate_audio_format,
            download_speed_limit_bytes_per_second=request.download_speed_limit_bytes_per_second,
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
        playlist_count: int | None = None,
        duration_seconds: int | None = None,
        estimated_file_size_bytes: int | None = None,
        is_file_size_estimated: bool = False,
    ) -> DownloadTask | None:
        with self._lock:
            task_index = self._task_index_by_id.get(task_id)

            if task_index is None:
                return None

            current_task = self._tasks[task_index]
            updated_task = current_task.with_metadata(
                title=title,
                video_quality=video_quality,
                playlist_count=playlist_count,
                duration_seconds=duration_seconds,
                estimated_file_size_bytes=estimated_file_size_bytes,
                is_file_size_estimated=is_file_size_estimated,
            )
            self._tasks[task_index] = updated_task

            return updated_task

    def update_download_speed_limit_for_mutable_tasks(
        self,
        *,
        bytes_per_second: int | None,
    ) -> tuple[DownloadTask, ...]:
        with self._lock:
            updated_tasks: list[DownloadTask] = []

            for task_index, task in enumerate(self._tasks):
                if not can_update_download_speed_limit(task):
                    continue

                updated_task = task.with_download_speed_limit(
                    download_speed_limit_bytes_per_second=bytes_per_second,
                )
                self._tasks[task_index] = updated_task
                updated_tasks.append(updated_task)

            return tuple(updated_tasks)

    def update_download_speed_limit_for_downloadable_tasks(
        self,
        *,
        bytes_per_second: int | None,
    ) -> tuple[DownloadTask, ...]:
        return self.update_download_speed_limit_for_mutable_tasks(
            bytes_per_second=bytes_per_second,
        )

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
            return any(build_media_source_key(url=task.url.value) == source_key for task in self._tasks)

    def get_task_by_url(self, url: str) -> DownloadTask | None:
        source_key = build_media_source_key(url=url)

        with self._lock:
            for task in self._tasks:
                if build_media_source_key(url=task.url.value) == source_key:
                    return task

        return None

    def _rebuild_task_index(self) -> None:
        self._task_index_by_id = {task.task_id: task_index for task_index, task in enumerate(self._tasks)}
