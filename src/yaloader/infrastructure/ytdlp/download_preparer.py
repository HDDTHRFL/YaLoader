from __future__ import annotations

import importlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self, cast

from loguru import logger

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.prepared_download import PreparedDownload
from yaloader.application.ports.downloader import CancellationToken
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.infrastructure.ytdlp.metadata_extractor import (
    extract_playlist_count,
    extract_title,
    select_metadata_info,
)
from yaloader.infrastructure.ytdlp.options_builder import YtDlpOptions, YtDlpOptionsBuilder


class DownloadPreparationCancelledError(RuntimeError):
    pass


class YoutubeDLPreparationRuntime(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

    def extract_info(self, url: str, download: bool = False) -> object: ...


class YoutubeDLPreparationFactory(Protocol):
    def __call__(self, params: YtDlpOptions) -> YoutubeDLPreparationRuntime: ...


@dataclass(frozen=True, slots=True)
class YtDlpDownloadPreparer:
    youtube_dl_factory: YoutubeDLPreparationFactory
    options_builder: YtDlpOptionsBuilder

    @classmethod
    def create_default(cls, *, cookies_file: Path | None = None) -> YtDlpDownloadPreparer:
        return cls(
            youtube_dl_factory=load_youtube_dl_preparation_factory(),
            options_builder=YtDlpOptionsBuilder(cookies_file=cookies_file),
        )

    def prepare(
        self,
        task: DownloadTask,
        cancellation_token: CancellationToken | None = None,
    ) -> PreparedDownload:
        self._raise_if_cancel_requested(cancellation_token=cancellation_token)

        request = self._build_request_from_task(task=task)
        options = self._build_options(request=request)

        logger.debug(
            "Download preparation started. task_id={} url={} playlist={}",
            task.task_id,
            task.url.value,
            task.include_playlist,
        )

        with self.youtube_dl_factory(options) as downloader:
            raw_info = downloader.extract_info(task.url.value, download=False)

        self._raise_if_cancel_requested(cancellation_token=cancellation_token)

        prepared_download = build_prepared_download(
            task=task,
            raw_info=raw_info,
        )

        logger.debug(
            "Download preparation finished. task_id={} title={} playlist_count={}",
            task.task_id,
            prepared_download.title,
            prepared_download.playlist_count,
        )

        return prepared_download

    def _build_options(self, *, request: DownloadRequest) -> YtDlpOptions:
        options = self.options_builder.build(request=request)
        options["quiet"] = True
        options["no_warnings"] = True
        options["skip_download"] = True
        options["simulate"] = True
        options["noprogress"] = True

        return options

    def _build_request_from_task(self, *, task: DownloadTask) -> DownloadRequest:
        return DownloadRequest(
            url=task.url.value,
            target_dir=task.target_dir,
            mode=task.mode,
            output_format=task.output_format,
            video_quality=task.video_quality,
            include_playlist=task.include_playlist,
            download_speed_limit_bytes_per_second=task.download_speed_limit_bytes_per_second,
        )

    def _raise_if_cancel_requested(
        self,
        *,
        cancellation_token: CancellationToken | None,
    ) -> None:
        if cancellation_token is not None and cancellation_token.is_cancel_requested:
            raise DownloadPreparationCancelledError


def build_prepared_download(
    *,
    task: DownloadTask,
    raw_info: object,
) -> PreparedDownload:
    media_info = select_metadata_info(
        raw_info=raw_info,
        include_playlist=task.include_playlist,
    )

    return PreparedDownload(
        task_id=task.task_id,
        url=task.url.value,
        title=extract_title(media_info=media_info),
        playlist_count=(
            extract_playlist_count(media_info=media_info) if task.include_playlist else None
        ),
        raw_info=copy_string_key_mapping(value=raw_info),
    )


def copy_string_key_mapping(*, value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}

    copied_mapping: dict[str, object] = {}

    for key, mapping_value in value.items():
        if isinstance(key, str):
            copied_mapping[key] = mapping_value

    return copied_mapping


def load_youtube_dl_preparation_factory() -> YoutubeDLPreparationFactory:
    ytdlp_module = importlib.import_module("yt_dlp")
    return cast(YoutubeDLPreparationFactory, ytdlp_module.YoutubeDL)
