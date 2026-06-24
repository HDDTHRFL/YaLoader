from __future__ import annotations

from pathlib import Path

from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality
from yaloader.ui.controllers.queue_input_controller import QueueInputController


def test_add_from_input_rejects_empty_url(tmp_path: Path) -> None:
    queue_service = DownloadQueueService()
    controller = QueueInputController(queue_service=queue_service)

    update = controller.add_from_input(
        url="   ",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )

    assert update.added_task is None
    assert update.metadata_request is None
    assert update.status_message == "Сначала вставьте ссылку"
    assert update.should_clear_url_input is False
    assert update.should_focus_url_input is True
    assert queue_service.count() == 0


def test_add_from_input_rejects_invalid_url(tmp_path: Path) -> None:
    queue_service = DownloadQueueService()
    controller = QueueInputController(queue_service=queue_service)

    update = controller.add_from_input(
        url="not-a-url",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )

    assert update.added_task is None
    assert update.metadata_request is None
    assert update.status_message is not None
    assert update.status_message.startswith("Некорректная задача загрузки:")
    assert update.should_clear_url_input is False
    assert update.should_focus_url_input is True
    assert queue_service.count() == 0


def test_add_from_input_creates_video_download_task(tmp_path: Path) -> None:
    queue_service = DownloadQueueService()
    controller = QueueInputController(queue_service=queue_service)

    update = controller.add_from_input(
        url=" https://www.youtube.com/watch?v=test ",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.P1080,
    )

    assert update.added_task is not None
    assert update.metadata_request is not None
    assert update.status_message == "Добавлено в очередь. Определяем доступное качество..."
    assert update.should_clear_url_input is True
    assert update.should_focus_url_input is True

    assert update.added_task.url.value == "https://www.youtube.com/watch?v=test"
    assert update.added_task.target_dir == tmp_path
    assert update.added_task.mode is DownloadMode.VIDEO
    assert update.added_task.output_format is OutputFormat.MP4
    assert update.added_task.video_quality is VideoQuality.P1080

    assert update.metadata_request.mode is DownloadMode.VIDEO
    assert update.metadata_request.output_format is OutputFormat.MP4
    assert update.metadata_request.video_quality is VideoQuality.P1080
    assert queue_service.list_tasks() == (update.added_task,)


def test_add_from_input_creates_audio_download_task(tmp_path: Path) -> None:
    queue_service = DownloadQueueService()
    controller = QueueInputController(queue_service=queue_service)

    update = controller.add_from_input(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        output_format=OutputFormat.MP3,
        video_quality=VideoQuality.BEST,
    )

    assert update.added_task is not None
    assert update.metadata_request is not None
    assert update.status_message == "Добавлено в очередь: 1"

    assert update.added_task.mode is DownloadMode.AUDIO
    assert update.added_task.output_format is OutputFormat.MP3
    assert update.metadata_request.mode is DownloadMode.AUDIO
    assert queue_service.count() == 1


def test_add_from_input_rejects_duplicate_url(tmp_path: Path) -> None:
    queue_service = DownloadQueueService()
    controller = QueueInputController(queue_service=queue_service)

    first_update = controller.add_from_input(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )
    second_update = controller.add_from_input(
        url="https://youtu.be/test?si=shared",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )

    assert first_update.added_task is not None
    assert second_update.added_task is None
    assert second_update.metadata_request is None
    assert second_update.status_message == "Эта ссылка уже есть в очереди"
    assert second_update.should_clear_url_input is False
    assert second_update.should_focus_url_input is True
    assert queue_service.count() == 1


def test_add_from_input_passes_download_speed_limit_to_task(tmp_path: Path) -> None:
    queue_service = DownloadQueueService()
    controller = QueueInputController(queue_service=queue_service)

    update = controller.add_from_input(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
        download_speed_limit_bytes_per_second=1_048_576,
    )

    assert update.added_task is not None
    assert update.added_task.download_speed_limit_bytes_per_second == 1_048_576
    assert update.metadata_request is not None
    assert update.metadata_request.download_speed_limit_bytes_per_second == 1_048_576


def test_add_from_input_uses_mp3_for_soundcloud_when_selected_format_is_video(
    tmp_path: Path,
) -> None:
    queue_service = DownloadQueueService()
    controller = QueueInputController(queue_service=queue_service)

    update = controller.add_from_input(
        url="https://soundcloud.com/artist/track",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )

    assert update.added_task is not None
    assert update.metadata_request is not None
    assert update.status_message == "Добавлено в очередь: 1"

    assert update.added_task.mode is DownloadMode.AUDIO
    assert update.added_task.output_format is OutputFormat.MP3
    assert update.metadata_request.mode is DownloadMode.AUDIO
    assert update.metadata_request.output_format is OutputFormat.MP3
    assert queue_service.count() == 1


def test_add_from_input_keeps_explicit_audio_format_for_soundcloud(tmp_path: Path) -> None:
    queue_service = DownloadQueueService()
    controller = QueueInputController(queue_service=queue_service)

    update = controller.add_from_input(
        url="https://soundcloud.com/artist/track",
        target_dir=tmp_path,
        output_format=OutputFormat.M4A,
        video_quality=VideoQuality.BEST,
    )

    assert update.added_task is not None
    assert update.metadata_request is not None

    assert update.added_task.mode is DownloadMode.AUDIO
    assert update.added_task.output_format is OutputFormat.M4A
    assert update.metadata_request.mode is DownloadMode.AUDIO
    assert update.metadata_request.output_format is OutputFormat.M4A


def test_add_from_input_accepts_ytdlp_auto_http_source_url(tmp_path: Path) -> None:
    queue_service = DownloadQueueService()
    controller = QueueInputController(queue_service=queue_service)

    update = controller.add_from_input(
        url="https://vimeo.com/123456",
        target_dir=tmp_path,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )

    assert update.added_task is not None
    assert update.metadata_request is not None
    assert update.status_message == "Добавлено в очередь. Определяем доступное качество..."

    assert update.added_task.url.value == "https://vimeo.com/123456"
    assert update.added_task.mode is DownloadMode.VIDEO
    assert update.added_task.output_format is OutputFormat.MP4
    assert update.metadata_request.url == "https://vimeo.com/123456"
    assert update.metadata_request.mode is DownloadMode.VIDEO
    assert queue_service.count() == 1
