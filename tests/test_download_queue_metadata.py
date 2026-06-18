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
    assert updated_task.requested_video_quality is VideoQuality.BEST
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


def test_apply_metadata_updates_running_task_metadata_without_touching_requested_quality(
    tmp_path: Path,
) -> None:
    service = DownloadQueueService()
    task = service.add_download(
        request=create_video_request(
            target_dir=tmp_path,
            video_quality=VideoQuality.P2160,
        )
    )
    service.update_status(
        task_id=task.task_id,
        status=DownloadStatus.RUNNING,
    )

    updated_task = service.apply_metadata(
        task_id=task.task_id,
        title="Resolved title",
        video_quality=VideoQuality.P720,
    )

    assert updated_task is not None
    assert updated_task.status is DownloadStatus.RUNNING
    assert updated_task.title == "Resolved title"
    assert updated_task.video_quality is VideoQuality.P720
    assert updated_task.requested_video_quality is VideoQuality.P2160
    assert service.get_task(task_id=task.task_id) == updated_task


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


def test_queue_keeps_separate_audio_video_settings(tmp_path: Path) -> None:
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
        separate_audio_video_enabled=True,
        separate_audio_format=OutputFormat.M4A,
    )
    service = DownloadQueueService()

    task = service.add_download(request=request)

    assert task.separate_audio_video_enabled is True
    assert task.separate_audio_format is OutputFormat.M4A
