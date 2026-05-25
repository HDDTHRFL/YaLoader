from __future__ import annotations

import importlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self, cast

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.infrastructure.ytdlp.options_builder import YtDlpOptions, YtDlpOptionsBuilder

ANSI_ESCAPE_SEQUENCE_RE = re.compile(r"\x1b\[[0-9;]*m")
YOUTUBE_BOT_CHECK_MARKER = "Sign in to confirm"


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
    cookies_file: Path | None = None

    @classmethod
    def create_default(cls, *, cookies_file: Path | None = None) -> YtDlpDownloader:
        return cls(
            options_builder=YtDlpOptionsBuilder(cookies_file=cookies_file),
            backend=YtDlpPythonBackend.create_default(),
            cookies_file=cookies_file,
        )

    def download(self, task: DownloadTask) -> DownloadResult:
        request = self._build_request_from_task(task=task)
        options = self.options_builder.build(request=request)

        try:
            self.backend.download(urls=(task.url.value,), options=options)
        except Exception as error:
            return DownloadResult.failed(
                task_id=task.task_id,
                error_message=self._build_error_message(error=error),
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

    def _build_error_message(self, error: Exception) -> str:
        error_message = strip_ansi_escape_sequences(text=str(error)).strip()

        if YOUTUBE_BOT_CHECK_MARKER in error_message:
            cookies_file_text = (
                str(self.cookies_file) if self.cookies_file is not None else "cookies.txt"
            )
            return (
                "YouTube запросил подтверждение, что вы не бот. "
                f"Добавьте актуальный cookies.txt сюда: {cookies_file_text}. "
                "После этого повторите загрузку."
            )

        return error_message


def strip_ansi_escape_sequences(text: str) -> str:
    return ANSI_ESCAPE_SEQUENCE_RE.sub("", text)


def load_youtube_dl_factory() -> YoutubeDLFactory:
    ytdlp_module = importlib.import_module("yt_dlp")
    return cast(YoutubeDLFactory, ytdlp_module.YoutubeDL)
