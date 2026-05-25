from __future__ import annotations

import importlib
from collections.abc import Sequence
from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Self, cast

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.infrastructure.ytdlp.options_builder import YtDlpOptions, YtDlpOptionsBuilder


class YtDlpBackend(Protocol):
    def download(self, urls: Sequence[str], options: YtDlpOptions) -> None: ...


class YoutubeDLRuntime(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

    def download(self, url_list: list[str]) -> int | None: ...


class YoutubeDLFactory(Protocol):
    def __call__(self, params: YtDlpOptions) -> YoutubeDLRuntime: ...


@dataclass(frozen=True, slots=True)
class YtDlpPythonBackend:
    youtube_dl_factory: YoutubeDLFactory

    @classmethod
    def create_default(cls) -> YtDlpPythonBackend:
        return cls(youtube_dl_factory=load_youtube_dl_factory())

    def download(self, urls: Sequence[str], options: YtDlpOptions) -> None:
        with self.youtube_dl_factory(options) as downloader:
            result_code = downloader.download(list(urls))

        if result_code not in (None, 0):
            message = f"yt-dlp finished with non-zero result code: {result_code}"
            raise RuntimeError(message)


@dataclass(frozen=True, slots=True)
class YtDlpDownloader:
    options_builder: YtDlpOptionsBuilder
    backend: YtDlpBackend

    @classmethod
    def create_default(cls) -> YtDlpDownloader:
        return cls(
            options_builder=YtDlpOptionsBuilder(),
            backend=YtDlpPythonBackend.create_default(),
        )

    def download(self, task: DownloadTask) -> DownloadResult:
        request = self._build_request_from_task(task=task)
        options = self.options_builder.build(request=request)

        try:
            self.backend.download(urls=(task.url.value,), options=options)
        except Exception as error:
            return DownloadResult.failed(
                task_id=task.task_id,
                error_message=str(error),
            )

        return DownloadResult.completed(task_id=task.task_id)

    def _build_request_from_task(self, task: DownloadTask) -> DownloadRequest:
        return DownloadRequest(
            url=task.url.value,
            target_dir=task.target_dir,
            mode=task.mode,
            output_format=task.output_format,
            video_quality=task.video_quality,
            include_playlist=task.include_playlist,
        )


def load_youtube_dl_factory() -> YoutubeDLFactory:
    ytdlp_module = importlib.import_module("yt_dlp")
    return cast(YoutubeDLFactory, ytdlp_module.YoutubeDL)
