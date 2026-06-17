from __future__ import annotations

from typing import Final

from yaloader.domain.enums import DownloadMode, OutputFormat
from yaloader.domain.format_rules import get_download_mode_for_output_format
from yaloader.domain.source_platform import SourcePlatform, detect_source_platform

DEFAULT_AUDIO_ONLY_OUTPUT_FORMAT: Final = OutputFormat.MP3
DEFAULT_VIDEO_OUTPUT_FORMAT: Final = OutputFormat.MP4

AUDIO_ONLY_SOURCE_PLATFORMS: Final[frozenset[SourcePlatform]] = frozenset(
    {
        SourcePlatform.SOUNDCLOUD,
    }
)

VIDEO_CAPABLE_SOURCE_PLATFORMS: Final[frozenset[SourcePlatform]] = frozenset(
    {
        SourcePlatform.YOUTUBE,
        SourcePlatform.RUTUBE,
        SourcePlatform.VK_VIDEO,
        SourcePlatform.TWITCH,
    }
)


def is_audio_only_source_platform(*, platform: SourcePlatform) -> bool:
    return platform in AUDIO_ONLY_SOURCE_PLATFORMS


def is_audio_only_source_url(*, url: str) -> bool:
    return is_audio_only_source_platform(platform=detect_source_platform(url=url))


def is_video_capable_source_platform(*, platform: SourcePlatform) -> bool:
    return platform in VIDEO_CAPABLE_SOURCE_PLATFORMS


def is_video_capable_source_url(*, url: str) -> bool:
    return is_video_capable_source_platform(platform=detect_source_platform(url=url))


def resolve_output_format_for_source_url(
    *,
    url: str,
    selected_output_format: OutputFormat,
) -> OutputFormat:
    platform = detect_source_platform(url=url)

    if not is_audio_only_source_platform(platform=platform):
        return selected_output_format

    return resolve_output_format_for_audio_only_source(
        selected_output_format=selected_output_format,
    )


def resolve_default_output_format_for_source_url(
    *,
    url: str,
    selected_output_format: OutputFormat,
) -> OutputFormat:
    platform = detect_source_platform(url=url)

    if is_audio_only_source_platform(platform=platform):
        return resolve_output_format_for_audio_only_source(
            selected_output_format=selected_output_format,
        )

    if not is_video_capable_source_platform(platform=platform):
        return selected_output_format

    selected_mode = get_download_mode_for_output_format(output_format=selected_output_format)

    if selected_mode is DownloadMode.AUDIO:
        return DEFAULT_VIDEO_OUTPUT_FORMAT

    return selected_output_format


def resolve_output_format_for_audio_only_source(
    *,
    selected_output_format: OutputFormat,
) -> OutputFormat:
    selected_mode = get_download_mode_for_output_format(output_format=selected_output_format)

    if selected_mode is DownloadMode.AUDIO:
        return selected_output_format

    return DEFAULT_AUDIO_ONLY_OUTPUT_FORMAT
