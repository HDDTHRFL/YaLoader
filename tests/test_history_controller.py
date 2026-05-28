from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.application.services.download_history_service import DownloadHistoryService
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.ui.controllers.history_controller import HistoryController


def test_load_returns_history_records(tmp_path: Path) -> None:
    history_service = DownloadHistoryService(history_file=tmp_path / "download_history.json")
    queue_service = DownloadQueueService()
    controller = HistoryController(
        history_service=history_service,
        queue_service=queue_service,
    )
    record = create_history_record(
        url="https://www.youtube.com/watch?v=first",
        target_dir=tmp_path,
    )
    history_service.append(record=record)

    update = controller.load()

    assert update.records == (record,)
    assert update.status_message is None


def test_clear_removes_history_records_and_requests_download_history_flags_clear(
    tmp_path: Path,
) -> None:
    history_service = DownloadHistoryService(history_file=tmp_path / "download_history.json")
    queue_service = DownloadQueueService()
    controller = HistoryController(
        history_service=history_service,
        queue_service=queue_service,
    )
    history_service.append(
        record=create_history_record(
            url="https://www.youtube.com/watch?v=first",
            target_dir=tmp_path,
        )
    )

    update = controller.clear()

    assert update.records == ()
    assert update.should_clear_download_history_flags is True
    assert update.status_message == "История очищена. Удалено записей: 1"
    assert history_service.load() == ()


def test_clear_empty_history_returns_empty_status(tmp_path: Path) -> None:
    history_service = DownloadHistoryService(history_file=tmp_path / "download_history.json")
    queue_service = DownloadQueueService()
    controller = HistoryController(
        history_service=history_service,
        queue_service=queue_service,
    )

    update = controller.clear()

    assert update.records == ()
    assert update.should_clear_download_history_flags is True
    assert update.status_message == "История уже пустая"


def test_remove_record_removes_selected_history_record(tmp_path: Path) -> None:
    history_service = DownloadHistoryService(history_file=tmp_path / "download_history.json")
    queue_service = DownloadQueueService()
    controller = HistoryController(
        history_service=history_service,
        queue_service=queue_service,
    )
    first_record = create_history_record(
        url="https://www.youtube.com/watch?v=first",
        target_dir=tmp_path,
    )
    second_record = create_history_record(
        url="https://www.youtube.com/watch?v=second",
        target_dir=tmp_path,
    )
    history_service.append(record=first_record)
    history_service.append(record=second_record)

    update = controller.remove_record(record=first_record)

    assert update.records == (second_record,)
    assert update.status_message == "Запись удалена из истории"


def test_remove_missing_record_returns_current_history_snapshot(tmp_path: Path) -> None:
    history_service = DownloadHistoryService(history_file=tmp_path / "download_history.json")
    queue_service = DownloadQueueService()
    controller = HistoryController(
        history_service=history_service,
        queue_service=queue_service,
    )
    existing_record = create_history_record(
        url="https://www.youtube.com/watch?v=existing",
        target_dir=tmp_path,
    )
    missing_record = create_history_record(
        url="https://www.youtube.com/watch?v=missing",
        target_dir=tmp_path,
    )
    history_service.append(record=existing_record)

    update = controller.remove_record(record=missing_record)

    assert update.records == (existing_record,)
    assert update.status_message == "Запись истории уже удалена"


def test_add_record_to_queue_creates_download_task_from_history_record(tmp_path: Path) -> None:
    history_service = DownloadHistoryService(history_file=tmp_path / "download_history.json")
    queue_service = DownloadQueueService()
    controller = HistoryController(
        history_service=history_service,
        queue_service=queue_service,
    )
    record = create_history_record(
        url="https://www.youtube.com/watch?v=first",
        target_dir=tmp_path,
        video_quality=VideoQuality.BEST,
        resolved_video_quality=VideoQuality.P1080,
    )

    update = controller.add_record_to_queue(record=record)

    assert update.added_task is not None
    assert update.metadata_request is not None
    assert update.status_message == "Задача из истории добавлена в очередь загрузок"

    assert update.added_task.url.value == record.url
    assert update.added_task.target_dir == record.target_dir
    assert update.added_task.mode is record.mode
    assert update.added_task.output_format is record.output_format
    assert update.added_task.video_quality is VideoQuality.BEST
    assert update.added_task.requested_video_quality is VideoQuality.BEST

    assert update.metadata_request.video_quality is VideoQuality.BEST
    assert queue_service.list_tasks() == (update.added_task,)


def test_add_record_to_queue_rejects_duplicate_url(tmp_path: Path) -> None:
    history_service = DownloadHistoryService(history_file=tmp_path / "download_history.json")
    queue_service = DownloadQueueService()
    controller = HistoryController(
        history_service=history_service,
        queue_service=queue_service,
    )
    record = create_history_record(
        url="https://www.youtube.com/watch?v=first",
        target_dir=tmp_path,
    )

    first_update = controller.add_record_to_queue(record=record)
    second_update = controller.add_record_to_queue(record=record)

    assert first_update.added_task is not None
    assert second_update.added_task is None
    assert second_update.status_message == "Эта ссылка уже есть в очереди"
    assert queue_service.count() == 1


def test_add_record_to_queue_returns_validation_error_for_unsupported_url(
    tmp_path: Path,
) -> None:
    history_service = DownloadHistoryService(history_file=tmp_path / "download_history.json")
    queue_service = DownloadQueueService()
    controller = HistoryController(
        history_service=history_service,
        queue_service=queue_service,
    )
    record = create_history_record(
        url="https://example.com/video",
        target_dir=tmp_path,
    )

    update = controller.add_record_to_queue(record=record)

    assert update.added_task is None
    assert update.metadata_request is None
    assert update.status_message is not None
    assert update.status_message.startswith("Не удалось добавить из истории:")
    assert queue_service.count() == 0


def create_history_record(
    *,
    url: str,
    target_dir: Path,
    video_quality: VideoQuality = VideoQuality.BEST,
    resolved_video_quality: VideoQuality | None = VideoQuality.P1080,
) -> DownloadHistoryRecord:
    current_time = datetime(2026, 5, 27, 12, 0, tzinfo=UTC)

    return DownloadHistoryRecord(
        task_id=uuid4(),
        url=url,
        title="Test video title",
        target_dir=target_dir,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=video_quality,
        resolved_video_quality=resolved_video_quality,
        status=DownloadStatus.COMPLETED,
        created_at=current_time,
        finished_at=current_time,
    )
