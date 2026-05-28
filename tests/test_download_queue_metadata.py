from __future__ import annotations

from pathlib import Path

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality


def test_apply_metadata_updates_task_title_and_quality(tmp_path: Path) -> None:
    service = DownloadQueueService()
    task = service.add_download(request=create_video_request(target_dir=tmp_path))

    updated_task = service.apply_metadata(
        task_id=task.task_id,
        title="Resolved title",
        video_quality=VideoQuality.P720,
    )

    assert updated_task is not None
    assert updated_task.title == "Resolved title"
    assert updated_task.video_quality is VideoQuality.P720
    assert service.get_task(task_id=task.task_id) == updated_task


def test_apply_metadata_returns_none_for_missing_task(tmp_path: Path) -> None:
    service = DownloadQueueService()
    task = service.add_download(request=create_video_request(target_dir=tmp_path))
    service.remove_task(task_id=task.task_id)

    updated_task = service.apply_metadata(
        task_id=task.task_id,
        title="Resolved title",
        video_quality=VideoQuality.P720,
    )

    assert updated_task is None


def test_apply_metadata_does_not_change_running_task_quality(tmp_path: Path) -> None:
    service = DownloadQueueService()
    task = service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            video_quality=VideoQuality.P2160,
        )
    )
    running_task = service.update_status(
        task_id=task.task_id,
        status=DownloadStatus.RUNNING,
    )

    updated_task = service.apply_metadata(
        task_id=task.task_id,
        title="Resolved title",
        video_quality=VideoQuality.P720,
    )

    assert updated_task == running_task
    assert updated_task is not None
    assert updated_task.video_quality is VideoQuality.P2160


def create_video_request(
    *,
    target_dir: Path,
    video_quality: VideoQuality = VideoQuality.BEST,
) -> DownloadRequest:
    return DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=target_dir,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=video_quality,
    )
