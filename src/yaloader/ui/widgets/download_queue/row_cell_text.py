from __future__ import annotations

from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.source_platform import detect_source_platform, get_source_platform_queue_label

CHECKING_TEXT = "Checking..."
UNKNOWN_TEXT = "—"
BYTES_IN_KIB = 1024
BYTES_IN_MIB = BYTES_IN_KIB * 1024
BYTES_IN_GIB = BYTES_IN_MIB * 1024
SECONDS_IN_HOUR = 3600
SECONDS_IN_MINUTE = 60


def build_mode_cell_text(*, task: DownloadTask) -> str:
    platform = detect_source_platform(url=task.url.value)
    return build_two_line_cell_text(
        first_line=get_source_platform_queue_label(platform=platform),
        second_line=task.mode.value,
    )


def build_quality_cell_text(*, task: DownloadTask, is_metadata_pending: bool) -> str:
    return build_two_line_cell_text(
        first_line=task.video_quality.value,
        second_line=build_file_size_text(
            size_bytes=task.estimated_file_size_bytes,
            is_file_size_estimated=task.is_file_size_estimated,
            is_metadata_pending=is_metadata_pending,
        ),
    )


def build_file_cell_text(*, task: DownloadTask, is_metadata_pending: bool) -> str:
    return build_two_line_cell_text(
        first_line=task.output_format.value,
        second_line=build_duration_text(
            duration_seconds=task.duration_seconds,
            is_metadata_pending=is_metadata_pending,
        ),
    )


def build_two_line_cell_text(*, first_line: str, second_line: str) -> str:
    return f"{first_line}\n{second_line}"


def build_file_size_text(
    *,
    size_bytes: int | None,
    is_file_size_estimated: bool,
    is_metadata_pending: bool,
) -> str:
    if size_bytes is not None and is_file_size_estimated:
        return format_estimated_file_size(size_bytes=size_bytes)

    if size_bytes is not None:
        return format_file_size(size_bytes=size_bytes)

    if is_metadata_pending:
        return CHECKING_TEXT

    return UNKNOWN_TEXT


def build_duration_text(*, duration_seconds: int | None, is_metadata_pending: bool) -> str:
    if duration_seconds is not None:
        return format_duration(duration_seconds=duration_seconds)

    if is_metadata_pending:
        return CHECKING_TEXT

    return UNKNOWN_TEXT


def format_estimated_file_size(*, size_bytes: int) -> str:
    return f"~{format_file_size(size_bytes=size_bytes)}"


def format_file_size(*, size_bytes: int) -> str:
    if size_bytes >= BYTES_IN_GIB:
        return f"{size_bytes / BYTES_IN_GIB:.2f} GB"

    if size_bytes >= BYTES_IN_MIB:
        return f"{size_bytes / BYTES_IN_MIB:.1f} MB"

    if size_bytes >= BYTES_IN_KIB:
        return f"{size_bytes / BYTES_IN_KIB:.1f} KB"

    return f"{size_bytes} B"


def format_duration(*, duration_seconds: int) -> str:
    hours, remainder = divmod(duration_seconds, SECONDS_IN_HOUR)
    minutes, seconds = divmod(remainder, SECONDS_IN_MINUTE)

    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"

    return f"{minutes}:{seconds:02}"
