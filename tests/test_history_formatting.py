from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.ui.widgets.history.formatting import format_history_quality, format_history_title


def build_record(
    *,
    url: str,
    include_playlist: bool,
    title: str | None = "Test title",
    playlist_count: int | None = None,
) -> DownloadHistoryRecord:
    return DownloadHistoryRecord(
        task_id=uuid4(),
        url=url,
        include_playlist=include_playlist,
        title=title,
        playlist_count=playlist_count,
        target_dir=Path.cwd(),
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
        resolved_video_quality=VideoQuality.P1080,
        status=DownloadStatus.COMPLETED,
        created_at=datetime.now(tz=UTC),
        finished_at=datetime.now(tz=UTC),
    )


def test_format_history_quality_adds_playlist_suffix() -> None:
    record = build_record(
        url="https://www.youtube.com/playlist?list=PL123",
        include_playlist=True,
    )

    assert format_history_quality(record=record) == "best (1080p) · playlist"


def test_format_history_quality_adds_shorts_suffix() -> None:
    record = build_record(
        url="https://www.youtube.com/shorts/abc123",
        include_playlist=False,
    )

    assert format_history_quality(record=record) == "best (1080p) · shorts"


def test_format_history_quality_keeps_regular_video_without_suffix() -> None:
    record = build_record(
        url="https://www.youtube.com/watch?v=abc123",
        include_playlist=False,
    )

    assert format_history_quality(record=record) == "best (1080p)"


def test_format_history_title_adds_playlist_prefix_with_count() -> None:
    record = build_record(
        url="https://www.youtube.com/playlist?list=PL123",
        include_playlist=True,
        title="My playlist",
        playlist_count=99,
    )

    assert format_history_title(record=record) == "[PLAYLIST] · 99 · My playlist"


def test_format_history_title_adds_shorts_prefix() -> None:
    record = build_record(
        url="https://www.youtube.com/shorts/abc123",
        include_playlist=False,
        title="Short video",
    )

    assert format_history_title(record=record) == "[SHORTS] · Short video"
