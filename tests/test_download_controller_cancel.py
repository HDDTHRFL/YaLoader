from __future__ import annotations

from pathlib import Path
from threading import Event
from time import monotonic, sleep
from uuid import UUID

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.ports.downloader import CancellationToken, ProgressCallback
from yaloader.application.services.download_history_service import DownloadHistoryService
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.ui.controllers.download_controller import DownloadController


class BlockingDownloader:
    def __init__(self) -> None:
        self.started = Event()
        self.task_ids: list[UUID] = []

    def download(
        self,
        task: DownloadTask,
        progress_callback: ProgressCallback | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> DownloadResult:
        self.task_ids.append(task.task_id)
        self.started.set()

        while cancellation_token is not None and not cancellation_token.is_cancel_requested:
            sleep(0.01)

        return DownloadResult.canceled(task_id=task.task_id)


def test_cancel_pending_selected_task_marks_only_that_task(tmp_path: Path) -> None:
    queue_service = DownloadQueueService()
    history_service = DownloadHistoryService(history_file=tmp_path / "history.json")
    controller = DownloadController(
        queue_service=queue_service,
        history_service=history_service,
        downloader=BlockingDownloader(),
    )
    first_task = queue_service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            url="https://www.youtube.com/watch?v=first",
        )
    )
    second_task = queue_service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            url="https://www.youtube.com/watch?v=second",
        )
    )

    update = controller.cancel_tasks_download(task_ids=(first_task.task_id,))

    assert update.status_message == "Выбранная задача отменена"
    assert queue_service.get_task(task_id=first_task.task_id).status is DownloadStatus.CANCELED
    assert queue_service.get_task(task_id=second_task.task_id).status is DownloadStatus.PENDING
    assert len(history_service.load()) == 1

    controller.shutdown()


def test_cancel_active_selected_task_keeps_following_tasks_queued(tmp_path: Path) -> None:
    queue_service = DownloadQueueService()
    history_service = DownloadHistoryService(history_file=tmp_path / "history.json")
    downloader = BlockingDownloader()
    controller = DownloadController(
        queue_service=queue_service,
        history_service=history_service,
        downloader=downloader,
    )
    first_task = queue_service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            url="https://www.youtube.com/watch?v=first",
        )
    )
    second_task = queue_service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            url="https://www.youtube.com/watch?v=second",
        )
    )

    try:
        controller.start_downloadable_queue()

        assert wait_until(lambda: downloader.started.is_set())
        assert controller.active_task_id == first_task.task_id

        update = controller.cancel_tasks_download(task_ids=(first_task.task_id,))

        assert update.status_message == "Отмена выбранной загрузки... Частичные файлы будут удалены"
        assert queue_service.get_task(task_id=first_task.task_id).status is DownloadStatus.CANCELED
        assert queue_service.get_task(task_id=second_task.task_id).status is DownloadStatus.PENDING

        assert wait_until(
            lambda: poll_and_check_active_task(
                controller=controller,
                task_id=second_task.task_id,
            )
        )
        assert controller.active_task_id == second_task.task_id
    finally:
        controller.shutdown()


def poll_and_check_active_task(
    *,
    controller: DownloadController,
    task_id: UUID,
) -> bool:
    controller.poll()
    return controller.active_task_id == task_id


def wait_until(
    condition: object,
    *,
    timeout_seconds: float = 2.0,
) -> bool:
    if not callable(condition):
        return False

    deadline = monotonic() + timeout_seconds

    while monotonic() < deadline:
        if condition():
            return True

        sleep(0.01)

    return False


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
