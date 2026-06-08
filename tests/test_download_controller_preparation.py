from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Event
from time import monotonic, sleep
from uuid import UUID

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.dto.prepared_download import PreparedDownload
from yaloader.application.ports.downloader import CancellationToken, ProgressCallback
from yaloader.application.services.download_history_service import DownloadHistoryService
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.application.services.prepared_download_cache import PreparedDownloadCache
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.ui.controllers.download_controller import DownloadController


class BlockingDownloader:
    def __init__(self) -> None:
        self.started = Event()
        self.started_task_ids: list[UUID] = []

    def download(
        self,
        task: DownloadTask,
        progress_callback: ProgressCallback | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> DownloadResult:
        self.started_task_ids.append(task.task_id)
        self.started.set()

        while cancellation_token is not None and not cancellation_token.is_cancel_requested:
            sleep(0.01)

        return DownloadResult.canceled(task_id=task.task_id)


class RecordingDownloadPreparer:
    def __init__(self) -> None:
        self.started = Event()
        self.prepared_task_ids: list[UUID] = []

    def prepare(
        self,
        task: DownloadTask,
        cancellation_token: CancellationToken | None = None,
    ) -> PreparedDownload:
        self.prepared_task_ids.append(task.task_id)
        self.started.set()

        return PreparedDownload(
            task_id=task.task_id,
            url=task.url.value,
            title=f"Prepared {task.url.value[-3:]}",
            raw_info={"title": f"Prepared {task.url.value[-3:]}"},
        )


def test_start_tasks_while_active_prepares_new_pending_task_without_parallel_download(
    tmp_path: Path,
) -> None:
    queue_service = DownloadQueueService()
    history_service = DownloadHistoryService(history_file=tmp_path / "history.json")
    downloader = BlockingDownloader()
    preparer = RecordingDownloadPreparer()
    prepared_download_cache = PreparedDownloadCache()
    controller = DownloadController(
        queue_service=queue_service,
        history_service=history_service,
        downloader=downloader,
        download_preparer=preparer,
        prepared_download_cache=prepared_download_cache,
    )
    first_task = queue_service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            url="https://www.youtube.com/watch?v=active001",
        )
    )
    second_task = queue_service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            url="https://www.youtube.com/watch?v=pending002",
        )
    )

    try:
        controller.start_tasks(task_ids=(first_task.task_id,))

        assert wait_until(lambda: controller.active_task_id == first_task.task_id)

        update = controller.start_tasks(task_ids=(second_task.task_id,))

        assert update.status_message == "Добавлено в текущую очередь: 1"
        assert update.prepared_task_ids == (second_task.task_id,)
        assert (
            require_task(queue_service=queue_service, task_id=second_task.task_id).status
            is DownloadStatus.PENDING
        )

        assert wait_until(lambda: second_task.task_id in preparer.prepared_task_ids)
        assert downloader.started_task_ids == [first_task.task_id]
        assert prepared_download_cache.contains(task_id=second_task.task_id)

        preparation_update = controller.poll()

        assert second_task.task_id in preparation_update.completed_preparation_task_ids
        assert controller.active_task_id == first_task.task_id

        prepared_task = queue_service.get_task(task_id=second_task.task_id)

        assert prepared_task is not None
        assert prepared_task.title == "Prepared 002"
    finally:
        controller.shutdown()


def test_cancel_prepared_running_task_removes_prepared_cache_entry(
    tmp_path: Path,
) -> None:
    queue_service = DownloadQueueService()
    history_service = DownloadHistoryService(history_file=tmp_path / "history.json")
    downloader = BlockingDownloader()
    preparer = RecordingDownloadPreparer()
    prepared_download_cache = PreparedDownloadCache()
    controller = DownloadController(
        queue_service=queue_service,
        history_service=history_service,
        downloader=downloader,
        download_preparer=preparer,
        prepared_download_cache=prepared_download_cache,
    )
    task = queue_service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            url="https://www.youtube.com/watch?v=pending001",
        )
    )

    try:
        start_update = controller.start_tasks(task_ids=(task.task_id,))

        assert start_update.prepared_task_ids == (task.task_id,)

        assert wait_until(lambda: prepared_download_cache.contains(task_id=task.task_id))

        cancel_update = controller.cancel_tasks_download(task_ids=(task.task_id,))

        assert (
            cancel_update.status_message
            == "Отмена выбранной загрузки... Частичные файлы будут удалены"
        )
        assert (
            require_task(queue_service=queue_service, task_id=task.task_id).status
            is DownloadStatus.CANCELED
        )
        assert not prepared_download_cache.contains(task_id=task.task_id)
    finally:
        controller.shutdown()


def wait_until(
    condition: Callable[[], bool],
    *,
    timeout_seconds: float = 2.0,
) -> bool:
    deadline = monotonic() + timeout_seconds

    while monotonic() < deadline:
        if condition():
            return True

        sleep(0.01)

    return False


def require_task(
    *,
    queue_service: DownloadQueueService,
    task_id: UUID,
) -> DownloadTask:
    task = queue_service.get_task(task_id=task_id)

    assert task is not None

    return task


def create_video_request(
    *,
    target_dir: Path,
    url: str,
) -> DownloadRequest:
    return DownloadRequest(
        url=url,
        target_dir=target_dir,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )
