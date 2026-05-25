from __future__ import annotations

from typing import Final

from yaloader.domain.enums import DownloadMode, OutputFormat

VIDEO_OUTPUT_FORMATS: Final[frozenset[OutputFormat]] = frozenset(
    {
        OutputFormat.MP4,
        OutputFormat.WEBM,
    }
)

AUDIO_OUTPUT_FORMATS: Final[frozenset[OutputFormat]] = frozenset(
    {
        OutputFormat.MP3,
        OutputFormat.M4A,
    }
)


def get_download_mode_for_output_format(output_format: OutputFormat) -> DownloadMode:
    if output_format in VIDEO_OUTPUT_FORMATS:
        return DownloadMode.VIDEO

    if output_format in AUDIO_OUTPUT_FORMATS:
        return DownloadMode.AUDIO

    message = f"Unsupported output format: {output_format}"
    raise ValueError(message)


def is_output_format_allowed(mode: DownloadMode, output_format: OutputFormat) -> bool:
    return output_format in get_allowed_output_formats(mode=mode)


def get_allowed_output_formats(mode: DownloadMode) -> frozenset[OutputFormat]:
    if mode is DownloadMode.VIDEO:
        return VIDEO_OUTPUT_FORMATS

    return AUDIO_OUTPUT_FORMATS
