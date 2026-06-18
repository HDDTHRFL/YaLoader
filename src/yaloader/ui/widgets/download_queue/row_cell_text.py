from __future__ import annotations

from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode

CHECKING_TEXT = "Checking..."
UNKNOWN_TEXT = "—"
BYTES_IN_KIB = 1024
BYTES_IN_MIB = BYTES_IN_KIB * 1024
BYTES_IN_GIB = BYTES_IN_MIB * 1024
SECONDS_IN_HOUR = 3600
SECONDS_IN_MINUTE = 60


def build_mode_cell_text(*, task: DownloadTask) -> str:
    return build_two_line_cell_text(
        first_line=task.mode.value,
        second_line=build_output_format_cell_text(task=task),
    )


def build_output_format_cell_text(*, task: DownloadTask) -> str:
    if task.mode is DownloadMode.VIDEO and task.separate_audio_video_enabled:
        return f"{task.output_format.value} + {task.separate_audio_format.value}"

    return task.output_format.value


def build_quality_cell_text(*, task: DownloadTask, is_metadata_pending: bool) -> str:
    return build_two_line_cell_text(
        first_line=build_quality_title_text(task=task),
        second_line=build_file_size_text(
            size_bytes=task.estimated_file_size_bytes,
            is_file_size_estimated=task.is_file_size_estimated,
            is_metadata_pending=is_metadata_pending,
        ),
    )


def build_quality_title_text(*, task: DownloadTask) -> str:
    duration_suffix = build_duration_suffix(duration_seconds=task.duration_seconds)

    return f"{task.video_quality.value}{duration_suffix}"


def build_duration_suffix(*, duration_seconds: int | None) -> str:
    if duration_seconds is None:
        return ""

    return f" ({format_duration(duration_seconds=duration_seconds)})"


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
