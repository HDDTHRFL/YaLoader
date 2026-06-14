from __future__ import annotations

from pathlib import Path

from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality
from yaloader.domain.value_objects.media_url import MediaUrl
from yaloader.ui.widgets.download_queue.row_cell_text import (
    CHECKING_TEXT,
    build_duration_text,
    build_mode_cell_text,
    build_quality_cell_text,
    build_quality_title_text,
    format_duration,
    format_estimated_file_size,
    format_file_size,
)


def test_build_mode_cell_text_contains_mode_and_output_format() -> None:
    task = create_task(url="https://rutube.ru/video/1234567890abcdef/")

    assert build_mode_cell_text(task=task) == "video\nmp4"


def test_build_mode_cell_text_supports_audio_output_format() -> None:
    task = create_task(
        url="https://www.youtube.com/watch?v=test",
        mode=DownloadMode.AUDIO,
        output_format=OutputFormat.MP3,
    )

    assert build_mode_cell_text(task=task) == "audio\nmp3"


def test_build_quality_cell_text_contains_quality_and_checking_size() -> None:
    task = create_task(url="https://www.youtube.com/watch?v=test")

    assert build_quality_cell_text(task=task, is_metadata_pending=True) == f"best\n{CHECKING_TEXT}"


def test_build_quality_cell_text_contains_duration_after_quality() -> None:
    task = create_task(
        url="https://www.youtube.com/watch?v=test",
        duration_seconds=65,
        estimated_file_size_bytes=10 * 1024 * 1024,
    )

    assert build_quality_cell_text(task=task, is_metadata_pending=False) == "best (1:05)\n10.0 MB"


def test_build_quality_title_text_omits_unknown_duration() -> None:
    task = create_task(url="https://www.youtube.com/watch?v=test")

    assert build_quality_title_text(task=task) == "best"


def test_build_quality_cell_text_does_not_add_tilde_for_declared_size() -> None:
    task = create_task(
        url="https://www.youtube.com/watch?v=test",
        estimated_file_size_bytes=10 * 1024 * 1024,
        is_file_size_estimated=False,
    )

    assert build_quality_cell_text(task=task, is_metadata_pending=False) == "best\n10.0 MB"


def test_build_quality_cell_text_adds_tilde_for_estimated_size() -> None:
    task = create_task(
        url="https://rutube.ru/video/1234567890abcdef/",
        estimated_file_size_bytes=10 * 1024 * 1024,
        is_file_size_estimated=True,
    )

    assert build_quality_cell_text(task=task, is_metadata_pending=False) == "best\n~10.0 MB"


def test_build_duration_text_contains_duration() -> None:
    assert build_duration_text(duration_seconds=65, is_metadata_pending=False) == "1:05"


def test_build_duration_text_contains_checking_when_pending() -> None:
    assert build_duration_text(duration_seconds=None, is_metadata_pending=True) == CHECKING_TEXT


def test_format_estimated_file_size_adds_tilde() -> None:
    assert format_estimated_file_size(size_bytes=10 * 1024 * 1024) == "~10.0 MB"


def test_format_file_size_uses_mb() -> None:
    assert format_file_size(size_bytes=10 * 1024 * 1024) == "10.0 MB"


def test_format_duration_uses_hours_when_needed() -> None:
    assert format_duration(duration_seconds=3661) == "1:01:01"


def create_task(
    *,
    url: str,
    mode: DownloadMode = DownloadMode.VIDEO,
    output_format: OutputFormat = OutputFormat.MP4,
    duration_seconds: int | None = None,
    estimated_file_size_bytes: int | None = None,
    is_file_size_estimated: bool = False,
) -> DownloadTask:
    return DownloadTask.create(
        url=MediaUrl(value=url),
        target_dir=Path("C:/Downloads"),
        mode=mode,
        output_format=output_format,
        video_quality=VideoQuality.BEST,
        include_playlist=False,
    ).with_metadata(
        title="Test",
        video_quality=VideoQuality.BEST,
        duration_seconds=duration_seconds,
        estimated_file_size_bytes=estimated_file_size_bytes,
        is_file_size_estimated=is_file_size_estimated,
    )
