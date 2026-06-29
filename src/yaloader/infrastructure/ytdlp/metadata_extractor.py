from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from types import TracebackType
from typing import Protocol, Self, cast

from loguru import logger

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.media_metadata import MediaMetadataProbe
from yaloader.application.ports.process_runner import ProcessRunner
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality
from yaloader.infrastructure.ytdlp.options_builder import YtDlpOptions, YtDlpOptionsBuilder
from yaloader.infrastructure.ytdlp.runtime_environment import YtDlpRuntimeEnvironment
from yaloader.infrastructure.ytdlp.runtime_manager import (
    YtDlpRuntimeManager,
    load_bundled_ytdlp_module,
)

BITS_PER_BYTE = 8
KILOBITS_PER_SECOND_MULTIPLIER = 1000

RESOLUTION_HEIGHT_RE: Pattern[str] = re.compile(r"(?<!\d)\d{3,5}x(?P<height>\d{3,5})(?!\d)")
HEIGHT_TEXT_RE: Pattern[str] = re.compile(
    r"(?<!\d)(?P<height>2160|1440|1080|720|480|360|240|144)p?(?!\d)"
)

VIDEO_QUALITY_HEIGHT_LIMITS: Mapping[VideoQuality, int] = {
    VideoQuality.P2160: 2160,
    VideoQuality.P1440: 1440,
    VideoQuality.P1080: 1080,
    VideoQuality.P720: 720,
    VideoQuality.P480: 480,
    VideoQuality.P360: 360,
}


@dataclass(frozen=True, slots=True)
class FileSizeMetadata:
    size_bytes: int | None = None
    is_estimated: bool = False


class YoutubeDLMetadataRuntime(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

    def extract_info(self, url: str, download: bool = False) -> object: ...


class YoutubeDLMetadataFactory(Protocol):
    def __call__(self, params: YtDlpOptions) -> YoutubeDLMetadataRuntime: ...


@dataclass(frozen=True, slots=True)
class YtDlpMetadataExtractor:
    youtube_dl_factory: YoutubeDLMetadataFactory
    cookies_file: Path | None = None
    process_runner: ProcessRunner | None = None

    @classmethod
    def create_default(
        cls,
        *,
        cookies_file: Path | None = None,
        process_runner: ProcessRunner | None = None,
        runtime_manager: YtDlpRuntimeManager | None = None,
    ) -> YtDlpMetadataExtractor:
        return cls(
            youtube_dl_factory=load_youtube_dl_metadata_factory(
                runtime_manager=runtime_manager,
            ),
            cookies_file=cookies_file,
            process_runner=process_runner,
        )

    def extract(self, request: DownloadRequest) -> MediaMetadataProbe:
        options = self._build_options(request=request)

        logger.debug(
            "Media metadata extraction started. url={} playlist={} cookies_enabled={}",
            request.url,
            request.include_playlist,
            "cookiefile" in options,
        )

        runtime_environment = YtDlpRuntimeEnvironment(process_runner=self.process_runner)

        with runtime_environment.apply(), self.youtube_dl_factory(options) as downloader:
            raw_info = downloader.extract_info(request.url, download=False)

        media_info = select_metadata_info(
            raw_info=raw_info,
            include_playlist=request.include_playlist,
        )
        title = extract_title(media_info=media_info)
        available_video_heights = (
            ()
            if request.include_playlist
            else extract_available_video_heights(media_info=media_info)
        )
        playlist_count = (
            extract_playlist_count(media_info=media_info) if request.include_playlist else None
        )
        duration_seconds = (
            None if request.include_playlist else extract_duration_seconds(media_info=media_info)
        )
        file_size_metadata = (
            FileSizeMetadata()
            if request.include_playlist
            else extract_file_size_metadata_for_download_settings(
                media_info=media_info,
                mode=request.mode,
                output_format=request.output_format,
                video_quality=request.video_quality,
            )
        )

        logger.debug(
            "Media metadata extracted. url={} title={} heights={} playlist_count={} "
            "duration={} size={} size_estimated={}",
            request.url,
            title,
            available_video_heights,
            playlist_count,
            duration_seconds,
            file_size_metadata.size_bytes,
            file_size_metadata.is_estimated,
        )

        return MediaMetadataProbe(
            url=request.url,
            title=title,
            available_video_heights=available_video_heights,
            playlist_count=playlist_count,
            duration_seconds=duration_seconds,
            estimated_file_size_bytes=file_size_metadata.size_bytes,
            is_file_size_estimated=file_size_metadata.is_estimated,
        )

    def _build_options(self, *, request: DownloadRequest) -> YtDlpOptions:
        options = YtDlpOptionsBuilder(
            cookies_file=self.cookies_file,
            process_runner=self.process_runner,
        ).build(request=request)
        options["quiet"] = True
        options["no_warnings"] = True
        options["skip_download"] = True
        options["simulate"] = True
        options["noprogress"] = True
        options["noplaylist"] = not request.include_playlist

        if request.include_playlist:
            options["extract_flat"] = True

        return options


def select_metadata_info(
    *,
    raw_info: object,
    include_playlist: bool,
) -> Mapping[str, object]:
    if not isinstance(raw_info, Mapping):
        return {}

    if include_playlist:
        return raw_info

    return select_primary_media_info(raw_info=raw_info)


def select_primary_media_info(*, raw_info: object) -> Mapping[str, object]:
    if not isinstance(raw_info, Mapping):
        return {}

    if isinstance(raw_info.get("formats"), list):
        return raw_info

    entries = raw_info.get("entries")

    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
        return raw_info

    for entry in entries:
        if isinstance(entry, Mapping):
            return entry

    return raw_info


def extract_title(*, media_info: Mapping[str, object]) -> str | None:
    title = media_info.get("title")

    if not isinstance(title, str):
        return None

    normalized_title = title.strip()

    if not normalized_title:
        return None

    return normalized_title


def extract_playlist_count(*, media_info: Mapping[str, object]) -> int | None:
    for key in ("playlist_count", "n_entries"):
        value = normalize_positive_int(media_info.get(key))

        if value is not None:
            return value

    entries = media_info.get("entries")

    if isinstance(entries, Sequence) and not isinstance(entries, (str, bytes)):
        return len(entries)

    return None


def extract_available_video_heights(*, media_info: Mapping[str, object]) -> tuple[int, ...]:
    formats = media_info.get("formats")

    if not isinstance(formats, list):
        return ()

    heights: set[int] = set()

    for format_item in formats:
        if not isinstance(format_item, Mapping):
            continue

        normalized_height = extract_format_height(format_item=format_item)

        if normalized_height is not None:
            heights.add(normalized_height)

    return tuple(sorted(heights, reverse=True))


def extract_format_height(*, format_item: Mapping[str, object]) -> int | None:
    explicit_height = normalize_height(format_item.get("height"))

    if explicit_height is not None:
        return explicit_height

    for key in ("resolution", "format_note", "format_id", "format"):
        text_height = extract_height_from_text(format_item.get(key))

        if text_height is not None:
            return text_height

    return None


def extract_height_from_text(value: object) -> int | None:
    if not isinstance(value, str):
        return None

    normalized_text = value.strip()

    if not normalized_text:
        return None

    resolution_match = RESOLUTION_HEIGHT_RE.search(normalized_text)

    if resolution_match is not None:
        return normalize_positive_int(resolution_match.group("height"))

    height_match = HEIGHT_TEXT_RE.search(normalized_text)

    if height_match is not None:
        return normalize_positive_int(height_match.group("height"))

    return None


def extract_duration_seconds(*, media_info: Mapping[str, object]) -> int | None:
    return normalize_positive_int(media_info.get("duration"))


def extract_estimated_file_size_bytes(*, media_info: Mapping[str, object]) -> int | None:
    return extract_file_size_metadata(media_info=media_info).size_bytes


def extract_file_size_metadata(*, media_info: Mapping[str, object]) -> FileSizeMetadata:
    selected_file_size = extract_selected_file_size_metadata(media_info=media_info)

    if selected_file_size.size_bytes is not None:
        return selected_file_size

    declared_file_size = extract_declared_file_size_metadata(media_info=media_info)

    if declared_file_size.size_bytes is not None:
        return declared_file_size

    estimated_size = estimate_file_size_bytes_from_bitrate(media_info=media_info)

    if estimated_size is not None:
        return FileSizeMetadata(size_bytes=estimated_size, is_estimated=True)

    return FileSizeMetadata()


def extract_file_size_metadata_for_download_settings(
    *,
    media_info: Mapping[str, object],
    mode: DownloadMode,
    output_format: OutputFormat,
    video_quality: VideoQuality,
) -> FileSizeMetadata:
    direct_metadata = extract_file_size_metadata(media_info=media_info)

    if direct_metadata.size_bytes is not None:
        return direct_metadata

    selected_available_formats = select_available_formats_for_download_settings(
        media_info=media_info,
        mode=mode,
        output_format=output_format,
        video_quality=video_quality,
    )

    return extract_available_format_size_metadata(
        media_info=media_info,
        selected_formats=selected_available_formats,
    )


def extract_selected_file_size_metadata(*, media_info: Mapping[str, object]) -> FileSizeMetadata:
    selected_formats = extract_selected_format_mappings(media_info=media_info)

    if not selected_formats:
        return FileSizeMetadata()

    fallback_duration_seconds = extract_duration_seconds(media_info=media_info)

    return extract_selected_formats_size_metadata(
        selected_formats=selected_formats,
        fallback_duration_seconds=fallback_duration_seconds,
    )


def extract_selected_formats_size_metadata(
    *,
    selected_formats: tuple[Mapping[str, object], ...],
    fallback_duration_seconds: int | None,
) -> FileSizeMetadata:
    selected_size_bytes = 0
    has_size = False
    has_estimated_part = False

    for format_item in selected_formats:
        format_size = extract_single_format_size_metadata(
            format_item=format_item,
            fallback_duration_seconds=fallback_duration_seconds,
        )

        if format_size.size_bytes is None:
            continue

        selected_size_bytes += format_size.size_bytes
        has_size = True
        has_estimated_part = has_estimated_part or format_size.is_estimated

    if not has_size:
        return FileSizeMetadata()

    return FileSizeMetadata(
        size_bytes=selected_size_bytes,
        is_estimated=has_estimated_part,
    )


def extract_single_format_size_metadata(
    *,
    format_item: Mapping[str, object],
    fallback_duration_seconds: int | None,
) -> FileSizeMetadata:
    declared_file_size = extract_declared_file_size_metadata(media_info=format_item)

    if declared_file_size.size_bytes is not None:
        return declared_file_size

    estimated_size = estimate_file_size_bytes_from_bitrate(
        media_info=format_item,
        fallback_duration_seconds=fallback_duration_seconds,
    )

    if estimated_size is not None:
        return FileSizeMetadata(size_bytes=estimated_size, is_estimated=True)

    return FileSizeMetadata()


def extract_selected_format_mappings(
    *,
    media_info: Mapping[str, object],
) -> tuple[Mapping[str, object], ...]:
    selected_formats: list[Mapping[str, object]] = []

    for key in ("requested_formats", "requested_downloads"):
        value = media_info.get(key)

        if not isinstance(value, list):
            continue

        for item in value:
            if isinstance(item, Mapping):
                selected_formats.append(item)

    return tuple(selected_formats)


def select_available_formats_for_download_settings(
    *,
    media_info: Mapping[str, object],
    mode: DownloadMode,
    output_format: OutputFormat,
    video_quality: VideoQuality,
) -> tuple[Mapping[str, object], ...]:
    available_formats = extract_available_format_mappings(media_info=media_info)

    if mode is DownloadMode.AUDIO:
        audio_format = select_best_audio_format(
            formats=available_formats,
            output_format=output_format,
        )
        return () if audio_format is None else (audio_format,)

    video_format = select_best_video_format(
        formats=available_formats,
        output_format=output_format,
        video_quality=video_quality,
    )

    if video_format is None:
        return ()

    if format_has_audio(format_item=video_format):
        return (video_format,)

    audio_format = select_best_audio_format(
        formats=available_formats,
        output_format=OutputFormat.M4A,
    )

    if audio_format is None:
        return (video_format,)

    return (video_format, audio_format)


def extract_available_format_mappings(
    *,
    media_info: Mapping[str, object],
) -> tuple[Mapping[str, object], ...]:
    formats = media_info.get("formats")

    if not isinstance(formats, list):
        return ()

    return tuple(item for item in formats if isinstance(item, Mapping))


def select_best_video_format(
    *,
    formats: tuple[Mapping[str, object], ...],
    output_format: OutputFormat,
    video_quality: VideoQuality,
) -> Mapping[str, object] | None:
    candidates = tuple(
        format_item
        for format_item in formats
        if format_has_video(format_item=format_item)
        and format_matches_requested_height(
            format_item=format_item,
            video_quality=video_quality,
        )
    )

    if not candidates:
        return None

    matching_extension_candidates = tuple(
        format_item
        for format_item in candidates
        if format_matches_extension(format_item=format_item, output_format=output_format)
    )

    if matching_extension_candidates:
        candidates = matching_extension_candidates

    return max(candidates, key=build_video_format_score)


def select_best_audio_format(
    *,
    formats: tuple[Mapping[str, object], ...],
    output_format: OutputFormat,
) -> Mapping[str, object] | None:
    candidates = tuple(
        format_item for format_item in formats if format_has_audio(format_item=format_item)
    )

    if not candidates:
        return None

    matching_extension_candidates = tuple(
        format_item
        for format_item in candidates
        if format_matches_extension(format_item=format_item, output_format=output_format)
    )

    if matching_extension_candidates:
        candidates = matching_extension_candidates

    return max(candidates, key=build_audio_format_score)


def build_video_format_score(format_item: Mapping[str, object]) -> tuple[int, int, float]:
    has_audio_score = 1 if format_has_audio(format_item=format_item) else 0
    height = extract_format_height(format_item=format_item) or 0
    bitrate = extract_total_bitrate_kilobits_per_second(media_info=format_item) or 0.0

    return (has_audio_score, height, bitrate)


def build_audio_format_score(format_item: Mapping[str, object]) -> tuple[float, int]:
    bitrate = (
        normalize_positive_float(format_item.get("abr"))
        or extract_total_bitrate_kilobits_per_second(media_info=format_item)
        or 0.0
    )
    has_video_penalty = 0 if not format_has_video(format_item=format_item) else -1

    return (bitrate, has_video_penalty)


def format_matches_requested_height(
    *,
    format_item: Mapping[str, object],
    video_quality: VideoQuality,
) -> bool:
    height_limit = VIDEO_QUALITY_HEIGHT_LIMITS.get(video_quality)

    if height_limit is None:
        return True

    height = extract_format_height(format_item=format_item)

    if height is None:
        return False

    return height <= height_limit


def format_matches_extension(
    *,
    format_item: Mapping[str, object],
    output_format: OutputFormat,
) -> bool:
    extension = format_item.get("ext")

    return isinstance(extension, str) and extension.casefold() == output_format.value


def format_has_video(*, format_item: Mapping[str, object]) -> bool:
    video_codec = format_item.get("vcodec")

    if isinstance(video_codec, str):
        return video_codec.strip().casefold() != "none"

    return extract_format_height(format_item=format_item) is not None


def format_has_audio(*, format_item: Mapping[str, object]) -> bool:
    audio_codec = format_item.get("acodec")

    if isinstance(audio_codec, str):
        return audio_codec.strip().casefold() != "none"

    return normalize_positive_float(format_item.get("abr")) is not None


def extract_available_format_size_metadata(
    *,
    media_info: Mapping[str, object],
    selected_formats: tuple[Mapping[str, object], ...],
) -> FileSizeMetadata:
    if not selected_formats:
        return FileSizeMetadata()

    fallback_duration_seconds = extract_duration_seconds(media_info=media_info)

    return extract_selected_formats_size_metadata(
        selected_formats=selected_formats,
        fallback_duration_seconds=fallback_duration_seconds,
    )


def extract_declared_file_size_metadata(*, media_info: Mapping[str, object]) -> FileSizeMetadata:
    exact_size = normalize_positive_int(media_info.get("filesize"))

    if exact_size is not None:
        return FileSizeMetadata(size_bytes=exact_size, is_estimated=False)

    approximate_size = normalize_positive_int(media_info.get("filesize_approx"))

    if approximate_size is not None:
        return FileSizeMetadata(size_bytes=approximate_size, is_estimated=False)

    return FileSizeMetadata()


def estimate_file_size_bytes_from_bitrate(
    *,
    media_info: Mapping[str, object],
    fallback_duration_seconds: int | None = None,
) -> int | None:
    duration_seconds = extract_duration_seconds(media_info=media_info) or fallback_duration_seconds

    if duration_seconds is None:
        return None

    bitrate = extract_total_bitrate_kilobits_per_second(media_info=media_info)

    if bitrate is None:
        return None

    return calculate_file_size_bytes_from_bitrate(
        duration_seconds=duration_seconds,
        bitrate_kilobits_per_second=bitrate,
    )


def extract_total_bitrate_kilobits_per_second(
    *,
    media_info: Mapping[str, object],
) -> float | None:
    total_bitrate = normalize_positive_float(media_info.get("tbr"))

    if total_bitrate is not None:
        return total_bitrate

    video_bitrate = normalize_positive_float(media_info.get("vbr")) or 0.0
    audio_bitrate = normalize_positive_float(media_info.get("abr")) or 0.0
    combined_bitrate = video_bitrate + audio_bitrate

    if combined_bitrate <= 0:
        return None

    return combined_bitrate


def calculate_file_size_bytes_from_bitrate(
    *,
    duration_seconds: int,
    bitrate_kilobits_per_second: float,
) -> int:
    estimated_size = (
        duration_seconds
        * bitrate_kilobits_per_second
        * KILOBITS_PER_SECOND_MULTIPLIER
        / BITS_PER_BYTE
    )

    return max(1, int(estimated_size))


def normalize_positive_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int | float) and value > 0:
        return float(value)

    if isinstance(value, str):
        try:
            numeric_value = float(value.strip())
        except ValueError:
            return None

        if numeric_value > 0:
            return numeric_value

    return None


def normalize_height(value: object) -> int | None:
    return normalize_positive_int(value)


def normalize_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int) and value > 0:
        return value

    if isinstance(value, float) and value > 0:
        return int(value)

    if isinstance(value, str):
        stripped_value = value.strip()

        if stripped_value.isdigit():
            return int(stripped_value)

    return None


def load_youtube_dl_metadata_factory(
    *,
    runtime_manager: YtDlpRuntimeManager | None = None,
) -> YoutubeDLMetadataFactory:
    ytdlp_module = (
        load_bundled_ytdlp_module() if runtime_manager is None else runtime_manager.load_module()
    )
    return cast(YoutubeDLMetadataFactory, ytdlp_module.YoutubeDL)
