from __future__ import annotations

import importlib
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self, cast
from uuid import UUID

from loguru import logger

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.ports.downloader import CancellationToken, ProgressCallback
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.infrastructure.ytdlp.options_builder import YtDlpOptions, YtDlpOptionsBuilder

ANSI_ESCAPE_SEQUENCE_RE = re.compile(r"\x1b\[[0-9;]*m")
YOUTUBE_BOT_CHECK_MARKER = "Sign in to confirm"

YTDLP_STATUS_DOWNLOADING = "downloading"
YTDLP_STATUS_FINISHED = "finished"
YTDLP_STATUS_ERROR = "error"

PERCENT_MULTIPLIER = 100.0

YtDlpProgressInfo = Mapping[str, object]
YtDlpProgressHook = Callable[[YtDlpProgressInfo], None]


class DownloadCancelledError(RuntimeError):
    pass


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
        logger.debug("yt-dlp backend started. urls_count={}", len(urls))

        with self.youtube_dl_factory(options) as downloader:
            result_code = downloader.download(list(urls))

        if result_code not in (None, 0):
            message = f"yt-dlp finished with non-zero result code: {result_code}"
            raise RuntimeError(message)

        logger.debug("yt-dlp backend finished successfully.")


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

    def download(
        self,
        task: DownloadTask,
        progress_callback: ProgressCallback | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> DownloadResult:
        logger.info(
            "Download started. task_id={} url={} mode={} format={} quality={} target_dir={}",
            task.task_id,
            task.url.value,
            task.mode.value,
            task.output_format.value,
            task.video_quality.value,
            task.target_dir,
        )

        request = self._build_request_from_task(task=task)
        options = self.options_builder.build(request=request)
        existing_files = collect_files(download_dir=task.target_dir)

        logger.debug(
            "Download options prepared. task_id={} cookies_enabled={} existing_files_count={}",
            task.task_id,
            "cookiefile" in options,
            len(existing_files),
        )

        if progress_callback is not None:
            progress_callback(DownloadProgress.started(task_id=task.task_id))
            options["progress_hooks"] = [
                self._build_progress_hook(
                    task_id=task.task_id,
                    progress_callback=progress_callback,
                    cancellation_token=cancellation_token,
                )
            ]

        try:
            self.backend.download(urls=(task.url.value,), options=options)
        except DownloadCancelledError:
            removed_files_count = cleanup_created_files(
                download_dir=task.target_dir,
                existing_files=existing_files,
            )

            logger.info(
                "Download canceled by user. task_id={} removed_files_count={}",
                task.task_id,
                removed_files_count,
            )

            if progress_callback is not None:
                progress_callback(DownloadProgress.canceled(task_id=task.task_id))

            return DownloadResult.canceled(task_id=task.task_id)
        except Exception as error:
            error_message = self._build_error_message(error=error)
            logger.opt(exception=error).warning(
                "Download failed. task_id={} error={}",
                task.task_id,
                error_message,
            )

            if progress_callback is not None:
                progress_callback(DownloadProgress.failed(task_id=task.task_id))

            return DownloadResult.failed(
                task_id=task.task_id,
                error_message=error_message,
            )

        if cancellation_token is not None and cancellation_token.is_cancel_requested:
            removed_files_count = cleanup_created_files(
                download_dir=task.target_dir,
                existing_files=existing_files,
            )

            logger.info(
                "Download canceled after backend finished. task_id={} removed_files_count={}",
                task.task_id,
                removed_files_count,
            )

            if progress_callback is not None:
                progress_callback(DownloadProgress.canceled(task_id=task.task_id))

            return DownloadResult.canceled(task_id=task.task_id)

        if progress_callback is not None:
            progress_callback(DownloadProgress.completed(task_id=task.task_id))

        logger.info("Download completed. task_id={}", task.task_id)
        return DownloadResult.completed(task_id=task.task_id)

    def _build_request_from_task(self, task: DownloadTask) -> DownloadRequest:
        return DownloadRequest(
            url=task.url.value,
            target_dir=task.target_dir,
            mode=task.mode,
            output_format=task.output_format,
            video_quality=task.video_quality,
            include_playlist=task.include_playlist,
            download_speed_limit_bytes_per_second=(task.download_speed_limit_bytes_per_second),
        )

    def _build_progress_hook(
        self,
        *,
        task_id: UUID,
        progress_callback: ProgressCallback,
        cancellation_token: CancellationToken | None,
    ) -> YtDlpProgressHook:
        def hook(progress_info: YtDlpProgressInfo) -> None:
            if cancellation_token is not None and cancellation_token.is_cancel_requested:
                raise DownloadCancelledError

            progress = build_download_progress(
                task_id=task_id,
                progress_info=progress_info,
            )

            if progress is not None:
                progress_callback(progress)

        return hook

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


def build_download_progress(
    *,
    task_id: UUID,
    progress_info: YtDlpProgressInfo,
) -> DownloadProgress | None:
    status = str(progress_info.get("status", "")).lower()

    if status == YTDLP_STATUS_DOWNLOADING:
        return build_downloading_progress(
            task_id=task_id,
            progress_info=progress_info,
        )

    if status == YTDLP_STATUS_FINISHED:
        return DownloadProgress.processing(task_id=task_id)

    if status == YTDLP_STATUS_ERROR:
        return DownloadProgress.failed(task_id=task_id)

    return None


def build_downloading_progress(
    *,
    task_id: UUID,
    progress_info: YtDlpProgressInfo,
) -> DownloadProgress:
    downloaded_bytes = get_int_value(progress_info.get("downloaded_bytes"))
    total_bytes = get_total_bytes(progress_info=progress_info)
    speed_bytes_per_second = get_positive_int_value(progress_info.get("speed"))
    percent = calculate_percent(
        downloaded_bytes=downloaded_bytes,
        total_bytes=total_bytes,
    )
    status_text = "Загрузка" if percent is None else f"Загрузка {percent:.1f}%"

    return DownloadProgress(
        task_id=task_id,
        percent=percent,
        status_text=status_text,
        downloaded_bytes=downloaded_bytes,
        total_bytes=total_bytes,
        speed_bytes_per_second=speed_bytes_per_second,
    )


def get_total_bytes(progress_info: YtDlpProgressInfo) -> int | None:
    total_bytes = get_int_value(progress_info.get("total_bytes"))

    if total_bytes is not None:
        return total_bytes

    return get_int_value(progress_info.get("total_bytes_estimate"))


def get_positive_int_value(value: object) -> int | None:
    normalized_value = get_int_value(value)

    if normalized_value is None or normalized_value <= 0:
        return None

    return normalized_value


def get_int_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    return None


def calculate_percent(
    *,
    downloaded_bytes: int | None,
    total_bytes: int | None,
) -> float | None:
    if downloaded_bytes is None or total_bytes is None:
        return None

    if total_bytes <= 0:
        return None

    percent = downloaded_bytes / total_bytes * PERCENT_MULTIPLIER
    return max(0.0, min(PERCENT_MULTIPLIER, percent))


def strip_ansi_escape_sequences(text: str) -> str:
    return ANSI_ESCAPE_SEQUENCE_RE.sub("", text)


def collect_files(*, download_dir: Path) -> frozenset[Path]:
    if not download_dir.exists():
        logger.debug("Download directory does not exist before download. path={}", download_dir)
        return frozenset()

    files = frozenset(path.resolve() for path in download_dir.rglob("*") if path.is_file())
    logger.debug(
        "Collected existing files before download. path={} count={}", download_dir, len(files)
    )

    return files


def cleanup_created_files(*, download_dir: Path, existing_files: frozenset[Path]) -> int:
    if not download_dir.exists():
        logger.debug("Download directory does not exist during cleanup. path={}", download_dir)
        return 0

    removed_files_count = 0

    for file_path in sorted(download_dir.rglob("*"), reverse=True):
        if not file_path.is_file():
            continue

        resolved_path = file_path.resolve()

        if resolved_path in existing_files:
            continue

        try:
            file_path.unlink()
        except OSError as error:
            logger.warning(
                "Failed to remove partial download file. path={} error={}",
                file_path,
                error,
            )
            continue

        removed_files_count += 1
        logger.debug("Removed partial download file. path={}", file_path)

    return removed_files_count


def load_youtube_dl_factory() -> YoutubeDLFactory:
    ytdlp_module = importlib.import_module("yt_dlp")
    return cast(YoutubeDLFactory, ytdlp_module.YoutubeDL)
