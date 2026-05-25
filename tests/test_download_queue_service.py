from __future__ import annotations

from pathlib import Path

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality


def test_add_download_creates_pending_task(tmp_path: Path) -> None:
    service = DownloadQueueService()
    request = create_video_request(target_dir=tmp_path)

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
    first_request = create_video_request(
        target_dir=tmp_path,
        url="https://www.youtube.com/watch?v=first",
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )
    second_request = create_video_request(
        target_dir=tmp_path,
        url="https://www.youtube.com/watch?v=second",
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
    request = create_video_request(target_dir=tmp_path)

    task = service.add_download(request=request)

    assert service.get_task(task_id=task.task_id) == task


def test_update_status_updates_existing_task(tmp_path: Path) -> None:
    service = DownloadQueueService()
    request = create_video_request(target_dir=tmp_path)
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
    request = create_video_request(target_dir=tmp_path)
    task = service.add_download(request=request)
    result = DownloadResult.failed(
        task_id=task.task_id,
        error_message="network error",
    )

    updated_task = service.apply_result(result=result)

    assert updated_task is not None
    assert updated_task.status == DownloadStatus.FAILED
    assert updated_task.error_message == "network error"


def test_remove_task_removes_existing_task_and_rebuilds_index(tmp_path: Path) -> None:
    service = DownloadQueueService()
    first_task = service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            url="https://www.youtube.com/watch?v=first",
        )
    )
    second_task = service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            url="https://www.youtube.com/watch?v=second",
        )
    )

    removed_task = service.remove_task(task_id=first_task.task_id)

    assert removed_task == first_task
    assert service.list_tasks() == (second_task,)
    assert service.get_task(task_id=first_task.task_id) is None
    assert service.get_task(task_id=second_task.task_id) == second_task
    assert service.count() == 1


def test_remove_task_returns_none_for_missing_task(tmp_path: Path) -> None:
    service = DownloadQueueService()
    task = service.add_download(request=create_video_request(target_dir=tmp_path))
    service.remove_task(task_id=task.task_id)

    removed_task = service.remove_task(task_id=task.task_id)

    assert removed_task is None


def test_list_downloadable_tasks_skips_running_and_completed_tasks(tmp_path: Path) -> None:
    service = DownloadQueueService()
    pending_task = service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            url="https://www.youtube.com/watch?v=pending",
        )
    )
    running_task = service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            url="https://www.youtube.com/watch?v=running",
        )
    )
    completed_task = service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            url="https://www.youtube.com/watch?v=completed",
        )
    )

    service.update_status(task_id=running_task.task_id, status=DownloadStatus.RUNNING)
    service.update_status(task_id=completed_task.task_id, status=DownloadStatus.COMPLETED)

    downloadable_tasks = service.list_downloadable_tasks()

    assert downloadable_tasks == (pending_task,)


def create_video_request(
    *,
    target_dir: Path,
    url: str = "https://www.youtube.com/watch?v=test",
    output_format: OutputFormat = OutputFormat.MP4,
    video_quality: VideoQuality = VideoQuality.BEST,
) -> DownloadRequest:
    return DownloadRequest(
        url=url,
        target_dir=target_dir,
        mode=DownloadMode.VIDEO,
        output_format=output_format,
        video_quality=video_quality,
    )
