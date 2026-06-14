from __future__ import annotations

import importlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self, cast

from loguru import logger

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.media_metadata import MediaMetadataProbe
from yaloader.application.ports.process_runner import ProcessRunner
from yaloader.infrastructure.ytdlp.options_builder import REMOTE_COMPONENTS, YtDlpOptions
from yaloader.infrastructure.ytdlp.runtime_environment import YtDlpRuntimeEnvironment


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
    ) -> YtDlpMetadataExtractor:
        return cls(
            youtube_dl_factory=load_youtube_dl_metadata_factory(),
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
        estimated_file_size_bytes = (
            None
            if request.include_playlist
            else extract_estimated_file_size_bytes(media_info=media_info)
        )

        logger.debug(
            "Media metadata extracted. url={} title={} heights={} playlist_count={} "
            "duration={} size={}",
            request.url,
            title,
            available_video_heights,
            playlist_count,
            duration_seconds,
            estimated_file_size_bytes,
        )

        return MediaMetadataProbe(
            url=request.url,
            title=title,
            available_video_heights=available_video_heights,
            playlist_count=playlist_count,
            duration_seconds=duration_seconds,
            estimated_file_size_bytes=estimated_file_size_bytes,
        )

    def _build_options(self, *, request: DownloadRequest) -> YtDlpOptions:
        options: YtDlpOptions = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": not request.include_playlist,
            "extract_flat": request.include_playlist,
            "remote_components": REMOTE_COMPONENTS,
        }

        if self.cookies_file is not None and self.cookies_file.is_file():
            options["cookiefile"] = str(self.cookies_file)

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

        height = format_item.get("height")
        normalized_height = normalize_height(height)

        if normalized_height is not None:
            heights.add(normalized_height)

    return tuple(sorted(heights, reverse=True))


def extract_duration_seconds(*, media_info: Mapping[str, object]) -> int | None:
    return normalize_positive_int(media_info.get("duration"))


def extract_estimated_file_size_bytes(*, media_info: Mapping[str, object]) -> int | None:
    for key in ("filesize", "filesize_approx"):
        value = normalize_positive_int(media_info.get(key))

        if value is not None:
            return value

    formats = media_info.get("formats")

    if not isinstance(formats, list):
        return None

    sizes: list[int] = []

    for format_item in formats:
        if not isinstance(format_item, Mapping):
            continue

        for key in ("filesize", "filesize_approx"):
            value = normalize_positive_int(format_item.get(key))

            if value is not None:
                sizes.append(value)
                break

    if not sizes:
        return None

    return max(sizes)


def normalize_height(value: object) -> int | None:
    return normalize_positive_int(value)


def normalize_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int) and value > 0:
        return value

    if isinstance(value, float) and value > 0:
        return int(value)

    return None


def load_youtube_dl_metadata_factory() -> YoutubeDLMetadataFactory:
    ytdlp_module = importlib.import_module("yt_dlp")
    return cast(YoutubeDLMetadataFactory, ytdlp_module.YoutubeDL)
