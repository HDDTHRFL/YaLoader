from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.application.services.download_history_service import DownloadHistoryService
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality


def test_load_returns_empty_tuple_when_history_file_does_not_exist(tmp_path: Path) -> None:
    service = DownloadHistoryService(history_file=tmp_path / "download_history.json")

    records = service.load()

    assert records == ()


def test_append_saves_record_and_load_reads_it_back(tmp_path: Path) -> None:
    service = DownloadHistoryService(history_file=tmp_path / "download_history.json")
    record = create_history_record(url="https://www.youtube.com/watch?v=first")

    service.append(record=record)

    records = service.load()

    assert records == (record,)


def test_append_keeps_newest_record_first(tmp_path: Path) -> None:
    service = DownloadHistoryService(history_file=tmp_path / "download_history.json")
    first_record = create_history_record(url="https://www.youtube.com/watch?v=first")
    second_record = create_history_record(url="https://www.youtube.com/watch?v=second")

    service.append(record=first_record)
    service.append(record=second_record)

    records = service.load()

    assert records == (second_record, first_record)


def test_append_limits_records_count(tmp_path: Path) -> None:
    service = DownloadHistoryService(
        history_file=tmp_path / "download_history.json",
        max_records=2,
    )
    first_record = create_history_record(url="https://www.youtube.com/watch?v=first")
    second_record = create_history_record(url="https://www.youtube.com/watch?v=second")
    third_record = create_history_record(url="https://www.youtube.com/watch?v=third")

    service.append(record=first_record)
    service.append(record=second_record)
    service.append(record=third_record)

    records = service.load()

    assert records == (third_record, second_record)


def test_remove_by_task_id_removes_matching_record_and_keeps_others(tmp_path: Path) -> None:
    service = DownloadHistoryService(history_file=tmp_path / "download_history.json")
    first_record = create_history_record(url="https://www.youtube.com/watch?v=first")
    second_record = create_history_record(url="https://www.youtube.com/watch?v=second")

    service.append(record=first_record)
    service.append(record=second_record)

    removed_count = service.remove_by_task_id(task_id=first_record.task_id)

    assert removed_count == 1
    assert service.load() == (second_record,)


def test_remove_by_task_id_removes_history_file_when_last_record_removed(tmp_path: Path) -> None:
    history_file = tmp_path / "download_history.json"
    service = DownloadHistoryService(history_file=history_file)
    record = create_history_record(url="https://www.youtube.com/watch?v=first")
    service.append(record=record)

    removed_count = service.remove_by_task_id(task_id=record.task_id)

    assert removed_count == 1
    assert history_file.is_file() is False
    assert service.load() == ()


def test_remove_by_task_id_returns_zero_for_missing_record(tmp_path: Path) -> None:
    service = DownloadHistoryService(history_file=tmp_path / "download_history.json")
    record = create_history_record(url="https://www.youtube.com/watch?v=first")
    service.append(record=record)

    removed_count = service.remove_by_task_id(task_id=uuid4())

    assert removed_count == 0
    assert service.load() == (record,)


def test_clear_removes_history_file_and_returns_removed_count(tmp_path: Path) -> None:
    history_file = tmp_path / "download_history.json"
    service = DownloadHistoryService(history_file=history_file)
    service.append(record=create_history_record(url="https://www.youtube.com/watch?v=first"))
    service.append(record=create_history_record(url="https://www.youtube.com/watch?v=second"))

    removed_count = service.clear()

    assert removed_count == 2
    assert history_file.is_file() is False
    assert service.load() == ()


def test_load_returns_empty_tuple_for_invalid_json(tmp_path: Path) -> None:
    history_file = tmp_path / "download_history.json"
    history_file.write_text("{invalid json", encoding="utf-8")
    service = DownloadHistoryService(history_file=history_file)

    records = service.load()

    assert records == ()


def test_load_accepts_legacy_record_without_resolved_video_quality(tmp_path: Path) -> None:
    history_file = tmp_path / "download_history.json"
    current_time = datetime(2026, 5, 27, 12, 0, tzinfo=UTC)
    history_file.write_text(
        (
            "["
            "{"
            '"task_id":"00000000-0000-0000-0000-000000000001",'
            '"url":"https://www.youtube.com/watch?v=first",'
            '"target_dir":"C:/Downloads",'
            '"mode":"video",'
            '"output_format":"mp4",'
            '"video_quality":"best",'
            '"status":"completed",'
            f'"created_at":"{current_time.isoformat()}",'
            f'"finished_at":"{current_time.isoformat()}",'
            '"output_path":null,'
            '"error_message":null'
            "}"
            "]"
        ),
        encoding="utf-8",
    )
    service = DownloadHistoryService(history_file=history_file)

    records = service.load()

    assert len(records) == 1
    assert records[0].video_quality is VideoQuality.BEST
    assert records[0].resolved_video_quality is None


def create_history_record(*, url: str) -> DownloadHistoryRecord:
    current_time = datetime(2026, 5, 27, 12, 0, tzinfo=UTC)

    return DownloadHistoryRecord(
        task_id=uuid4(),
        url=url,
        target_dir=Path("C:/Downloads"),
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
        resolved_video_quality=VideoQuality.P1080,
        status=DownloadStatus.COMPLETED,
        created_at=current_time,
        finished_at=current_time,
    )
