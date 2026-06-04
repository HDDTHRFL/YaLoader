from __future__ import annotations

from pathlib import Path

from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.domain.enums import OutputFormat, VideoQuality
from yaloader.ui.controllers.queue_input_controller import QueueInputController


def test_add_playlist_url_sets_include_playlist_and_requests_metadata(
    tmp_path: Path,
) -> None:
    queue_service = DownloadQueueService()
    controller = QueueInputController(queue_service=queue_service)

    update = controller.add_from_input(
        url="https://www.youtube.com/playlist?list=PL123",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )

    assert update.added_task is not None
    assert update.added_task.include_playlist is True
    assert update.metadata_request is not None
    assert update.metadata_request.include_playlist is True
    assert update.status_message == "Плейлист добавлен в очередь загрузок"


def test_add_watch_url_with_list_keeps_single_video_metadata_resolution(
    tmp_path: Path,
) -> None:
    queue_service = DownloadQueueService()
    controller = QueueInputController(queue_service=queue_service)

    update = controller.add_from_input(
        url="https://www.youtube.com/watch?v=video123&list=PL123",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )

    assert update.added_task is not None
    assert update.added_task.include_playlist is False
    assert update.metadata_request is not None
    assert update.metadata_request.include_playlist is False
