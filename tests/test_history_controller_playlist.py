from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.application.services.download_history_service import DownloadHistoryService
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.ui.controllers.history_controller import HistoryController


def test_add_playlist_record_to_queue_preserves_include_playlist(
    tmp_path: Path,
) -> None:
    queue_service = DownloadQueueService()
    controller = HistoryController(
        history_service=DownloadHistoryService(history_file=tmp_path / "history.json"),
        queue_service=queue_service,
    )
    record = DownloadHistoryRecord(
        task_id=uuid4(),
        url="https://www.youtube.com/playlist?list=PL123",
        include_playlist=True,
        title="Test playlist",
        target_dir=tmp_path,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
        resolved_video_quality=VideoQuality.BEST,
        status=DownloadStatus.COMPLETED,
        created_at=datetime.now(tz=UTC),
        finished_at=datetime.now(tz=UTC),
    )

    update = controller.add_record_to_queue(record=record)

    assert update.added_task is not None
    assert update.added_task.include_playlist is True
    assert update.metadata_request is None
    assert update.status_message == "Плейлист из истории добавлен в очередь загрузок"


def test_add_single_video_record_to_queue_keeps_metadata_request(
    tmp_path: Path,
) -> None:
    queue_service = DownloadQueueService()
    controller = HistoryController(
        history_service=DownloadHistoryService(history_file=tmp_path / "history.json"),
        queue_service=queue_service,
    )
    record = DownloadHistoryRecord(
        task_id=uuid4(),
        url="https://www.youtube.com/watch?v=video123&list=PL123",
        include_playlist=False,
        title="Test video",
        target_dir=tmp_path,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
        resolved_video_quality=VideoQuality.BEST,
        status=DownloadStatus.COMPLETED,
        created_at=datetime.now(tz=UTC),
        finished_at=datetime.now(tz=UTC),
    )

    update = controller.add_record_to_queue(record=record)

    assert update.added_task is not None
    assert update.added_task.include_playlist is False
    assert update.metadata_request is not None
    assert update.metadata_request.include_playlist is False
