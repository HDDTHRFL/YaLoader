from __future__ import annotations

from threading import RLock

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.value_objects.media_url import MediaUrl


class DownloadQueueService:
    def __init__(self) -> None:
        self._lock = RLock()
        self._tasks: list[DownloadTask] = []

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
            self._tasks.append(task)

        return task

    def list_tasks(self) -> tuple[DownloadTask, ...]:
        with self._lock:
            return tuple(self._tasks)

    def count(self) -> int:
        with self._lock:
            return len(self._tasks)
