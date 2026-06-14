from __future__ import annotations

from pathlib import Path

from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality
from yaloader.domain.value_objects.media_url import MediaUrl
from yaloader.ui.widgets.download_queue.row_cell_text import (
    CHECKING_TEXT,
    build_file_cell_text,
    build_mode_cell_text,
    build_quality_cell_text,
    format_duration,
    format_file_size,
)


def test_build_mode_cell_text_contains_platform_and_mode() -> None:
    task = create_task(url="https://rutube.ru/video/1234567890abcdef/")

    assert build_mode_cell_text(task=task) == "▣ Rutube\nvideo"


def test_build_quality_cell_text_contains_quality_and_checking_size() -> None:
    task = create_task(url="https://www.youtube.com/watch?v=test")

    assert build_quality_cell_text(task=task, is_metadata_pending=True) == f"best\n{CHECKING_TEXT}"


def test_build_file_cell_text_contains_format_and_duration() -> None:
    task = create_task(
        url="https://www.youtube.com/watch?v=test",
        duration_seconds=65,
    )

    assert build_file_cell_text(task=task, is_metadata_pending=False) == "mp4\n1:05"


def test_format_file_size_uses_mb() -> None:
    assert format_file_size(size_bytes=10 * 1024 * 1024) == "10.0 MB"


def test_format_duration_uses_hours_when_needed() -> None:
    assert format_duration(duration_seconds=3661) == "1:01:01"


def create_task(
    *,
    url: str,
    duration_seconds: int | None = None,
) -> DownloadTask:
    return DownloadTask.create(
        url=MediaUrl(value=url),
        target_dir=Path("C:/Downloads"),
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
        include_playlist=False,
    ).with_metadata(
        title="Test",
        video_quality=VideoQuality.BEST,
        duration_seconds=duration_seconds,
        estimated_file_size_bytes=None,
    )
