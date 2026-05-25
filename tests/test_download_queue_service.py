from __future__ import annotations

from pathlib import Path

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality


def test_add_download_creates_pending_task(tmp_path: Path) -> None:
    service = DownloadQueueService()
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )

    task = service.add_download(request=request)

    assert task.url.value == "https://www.youtube.com/watch?v=test"
    assert task.target_dir == tmp_path
    assert task.mode == DownloadMode.VIDEO
    assert task.output_format == OutputFormat.MP4
    assert task.video_quality == VideoQuality.BEST
    assert task.status == DownloadStatus.PENDING
    assert service.count() == 1


def test_list_tasks_returns_tasks_in_creation_order(tmp_path: Path) -> None:
    service = DownloadQueueService()
    first_request = DownloadRequest(
        url="https://www.youtube.com/watch?v=first",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )
    second_request = DownloadRequest(
        url="https://www.youtube.com/watch?v=second",
        target_dir=tmp_path,
        output_format=OutputFormat.WEBM,
        video_quality=VideoQuality.P1080,
    )

    first_task = service.add_download(request=first_request)
    second_task = service.add_download(request=second_request)

    tasks = service.list_tasks()

    assert tasks == (first_task, second_task)
    assert first_task.task_id != second_task.task_id


def test_get_task_returns_task_by_id(tmp_path: Path) -> None:
    service = DownloadQueueService()
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )

    task = service.add_download(request=request)

    assert service.get_task(task_id=task.task_id) == task


def test_update_status_updates_existing_task(tmp_path: Path) -> None:
    service = DownloadQueueService()
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )
    task = service.add_download(request=request)

    updated_task = service.update_status(
        task_id=task.task_id,
        status=DownloadStatus.RUNNING,
    )

    assert updated_task is not None
    assert updated_task.task_id == task.task_id
    assert updated_task.status == DownloadStatus.RUNNING
    assert service.get_task(task_id=task.task_id) == updated_task


def test_apply_result_updates_task_status(tmp_path: Path) -> None:
    service = DownloadQueueService()
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )
    task = service.add_download(request=request)
    result = DownloadResult.failed(
        task_id=task.task_id,
        error_message="network error",
    )

    updated_task = service.apply_result(result=result)

    assert updated_task is not None
    assert updated_task.status == DownloadStatus.FAILED
    assert updated_task.error_message == "network error"
