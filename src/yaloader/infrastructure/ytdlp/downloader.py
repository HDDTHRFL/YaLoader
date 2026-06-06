from __future__ import annotations

import importlib
import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self, cast
from uuid import UUID

from loguru import logger

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.dto.prepared_download import PreparedDownload
from yaloader.application.ports.downloader import CancellationToken, ProgressCallback
from yaloader.application.ports.process_runner import ProcessRunner
from yaloader.application.services.prepared_download_cache import PreparedDownloadCache
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.infrastructure.ytdlp.options_builder import YtDlpOptions, YtDlpOptionsBuilder
from yaloader.infrastructure.ytdlp.output_naming import build_unique_output_template

ANSI_ESCAPE_SEQUENCE_RE = re.compile(r"\x1b\[[0-9;]*m")
YOUTUBE_BOT_CHECK_MARKER = "Sign in to confirm"

YTDLP_STATUS_DOWNLOADING = "downloading"
YTDLP_STATUS_FINISHED = "finished"
YTDLP_STATUS_ERROR = "error"

PERCENT_MULTIPLIER = 100.0
THROTTLE_SLEEP_STEP_SECONDS = 0.1
MAX_SINGLE_THROTTLE_SLEEP_SECONDS = 1.0
TEMPORARY_DOWNLOAD_FILE_SUFFIXES = (
    ".part",
    ".tmp",
    ".temp",
    ".ytdl",
)

YtDlpProgressInfo = Mapping[str, object]
YtDlpProgressHook = Callable[[YtDlpProgressInfo], None]


class DownloadCancelledError(RuntimeError):
    pass


class YtDlpBackend(Protocol):
    def download(self, urls: Sequence[str], options: YtDlpOptions) -> None: ...

    def download_prepared(
        self,
        *,
        prepared_download: PreparedDownload,
        options: YtDlpOptions,
    ) -> None: ...


class DownloadSpeedLimitProvider(Protocol):
    def get_download_speed_limit_bytes_per_second(self) -> int | None: ...


class YoutubeDLRuntime(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

    def download(self, url_list: list[str]) -> int | None: ...

    def process_ie_result(self, ie_result: object, download: bool = True) -> object: ...


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

    def download_prepared(
        self,
        *,
        prepared_download: PreparedDownload,
        options: YtDlpOptions,
    ) -> None:
        logger.debug(
            "yt-dlp prepared backend started. task_id={} title={}",
            prepared_download.task_id,
            prepared_download.title,
        )

        with self.youtube_dl_factory(options) as downloader:
            downloader.process_ie_result(prepared_download.raw_info, download=True)

        logger.debug(
            "yt-dlp prepared backend finished successfully. task_id={}",
            prepared_download.task_id,
        )


@dataclass(slots=True)
class DynamicDownloadSpeedThrottler:
    speed_limit_provider: DownloadSpeedLimitProvider | None
    _window_started_at: float = field(default_factory=time.monotonic)
    _window_downloaded_bytes: int | None = None
    _current_limit_bytes_per_second: int | None = None

    def throttle(
        self,
        *,
        downloaded_bytes: int | None,
        cancellation_token: CancellationToken | None,
    ) -> None:
        self._raise_if_cancel_requested(cancellation_token=cancellation_token)

        speed_limit = self._get_speed_limit()

        if speed_limit is None or downloaded_bytes is None:
            self._reset_window(downloaded_bytes=downloaded_bytes, speed_limit=speed_limit)
            return

        if self._should_reset_window(
            downloaded_bytes=downloaded_bytes,
            speed_limit=speed_limit,
        ):
            self._reset_window(downloaded_bytes=downloaded_bytes, speed_limit=speed_limit)
            return

        if self._window_downloaded_bytes is None:
            self._reset_window(downloaded_bytes=downloaded_bytes, speed_limit=speed_limit)
            return

        transferred_bytes = downloaded_bytes - self._window_downloaded_bytes

        if transferred_bytes <= 0:
            return

        expected_elapsed_seconds = transferred_bytes / speed_limit
        actual_elapsed_seconds = time.monotonic() - self._window_started_at
        sleep_seconds = expected_elapsed_seconds - actual_elapsed_seconds

        if sleep_seconds <= 0:
            return

        self._sleep_interruptibly(
            seconds=min(sleep_seconds, MAX_SINGLE_THROTTLE_SLEEP_SECONDS),
            cancellation_token=cancellation_token,
            speed_limit=speed_limit,
        )

    def _should_reset_window(
        self,
        *,
        downloaded_bytes: int,
        speed_limit: int,
    ) -> bool:
        if self._current_limit_bytes_per_second != speed_limit:
            return True

        if self._window_downloaded_bytes is None:
            return True

        return downloaded_bytes < self._window_downloaded_bytes

    def _reset_window(
        self,
        *,
        downloaded_bytes: int | None,
        speed_limit: int | None,
    ) -> None:
        self._window_started_at = time.monotonic()
        self._window_downloaded_bytes = downloaded_bytes
        self._current_limit_bytes_per_second = speed_limit

    def _sleep_interruptibly(
        self,
        *,
        seconds: float,
        cancellation_token: CancellationToken | None,
        speed_limit: int,
    ) -> None:
        deadline = time.monotonic() + seconds

        while True:
            self._raise_if_cancel_requested(cancellation_token=cancellation_token)

            if self._get_speed_limit() != speed_limit:
                self._reset_window(
                    downloaded_bytes=self._window_downloaded_bytes,
                    speed_limit=self._get_speed_limit(),
                )
                return

            remaining_seconds = deadline - time.monotonic()

            if remaining_seconds <= 0:
                return

            time.sleep(min(remaining_seconds, THROTTLE_SLEEP_STEP_SECONDS))

    def _get_speed_limit(self) -> int | None:
        if self.speed_limit_provider is None:
            return None

        return self.speed_limit_provider.get_download_speed_limit_bytes_per_second()

    def _raise_if_cancel_requested(self, *, cancellation_token: CancellationToken | None) -> None:
        if cancellation_token is not None and cancellation_token.is_cancel_requested:
            raise DownloadCancelledError


@dataclass(frozen=True, slots=True)
class YtDlpDownloader:
    options_builder: YtDlpOptionsBuilder
    backend: YtDlpBackend
    cookies_file: Path | None = None
    speed_limit_provider: DownloadSpeedLimitProvider | None = None
    prepared_download_cache: PreparedDownloadCache | None = None

    @classmethod
    def create_default(
        cls,
        *,
        cookies_file: Path | None = None,
        speed_limit_provider: DownloadSpeedLimitProvider | None = None,
        prepared_download_cache: PreparedDownloadCache | None = None,
        process_runner: ProcessRunner | None = None,
    ) -> YtDlpDownloader:
        return cls(
            options_builder=YtDlpOptionsBuilder(
                cookies_file=cookies_file,
                process_runner=process_runner,
            ),
            backend=YtDlpPythonBackend.create_default(),
            cookies_file=cookies_file,
            speed_limit_provider=speed_limit_provider,
            prepared_download_cache=prepared_download_cache,
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

        prepared_download = self._get_prepared_download(task=task)
        apply_prepared_output_template(
            options=options,
            task=task,
            prepared_download=prepared_download,
        )

        try:
            if prepared_download is not None and prepared_download.raw_info:
                self.backend.download_prepared(
                    prepared_download=prepared_download,
                    options=options,
                )
            else:
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

        output_path = detect_primary_output_path(
            download_dir=task.target_dir,
            existing_files=existing_files,
        )

        if progress_callback is not None:
            progress_callback(DownloadProgress.completed(task_id=task.task_id))

        logger.info(
            "Download completed. task_id={} output_path={}",
            task.task_id,
            output_path,
        )
        return DownloadResult.completed(
            task_id=task.task_id,
            output_path=output_path,
        )

    def _get_prepared_download(self, *, task: DownloadTask) -> PreparedDownload | None:
        if self.prepared_download_cache is None:
            return None

        prepared_download = self.prepared_download_cache.get(task_id=task.task_id)

        if prepared_download is None:
            return None

        if prepared_download.url != task.url.value:
            logger.warning(
                "Prepared download URL mismatch. task_id={} task_url={} prepared_url={}",
                task.task_id,
                task.url.value,
                prepared_download.url,
            )
            return None

        logger.debug(
            "Prepared download found in cache. task_id={} title={}",
            task.task_id,
            prepared_download.title,
        )
        return prepared_download

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
        throttler = DynamicDownloadSpeedThrottler(
            speed_limit_provider=self.speed_limit_provider,
        )

        def hook(progress_info: YtDlpProgressInfo) -> None:
            if cancellation_token is not None and cancellation_token.is_cancel_requested:
                raise DownloadCancelledError

            downloaded_bytes = get_int_value(progress_info.get("downloaded_bytes"))
            throttler.throttle(
                downloaded_bytes=downloaded_bytes,
                cancellation_token=cancellation_token,
            )
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


def apply_prepared_output_template(
    *,
    options: YtDlpOptions,
    task: DownloadTask,
    prepared_download: PreparedDownload | None,
) -> None:
    if prepared_download is None or prepared_download.title is None:
        return

    if task.include_playlist:
        return

    options["outtmpl"] = build_unique_output_template(
        target_dir=task.target_dir,
        title=prepared_download.title,
        output_extension=task.output_format.value,
    )


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
    info_dict = get_mapping_value(progress_info.get("info_dict"))
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
        playlist_index=get_playlist_index(progress_info=progress_info, info_dict=info_dict),
        playlist_count=get_playlist_count(progress_info=progress_info, info_dict=info_dict),
        current_title=get_non_empty_string(info_dict.get("title")),
        playlist_title=get_non_empty_string(info_dict.get("playlist_title")),
    )


def get_playlist_index(
    *,
    progress_info: YtDlpProgressInfo,
    info_dict: Mapping[str, object],
) -> int | None:
    return get_positive_int_value(progress_info.get("playlist_index")) or get_positive_int_value(
        info_dict.get("playlist_index")
    )


def get_playlist_count(
    *,
    progress_info: YtDlpProgressInfo,
    info_dict: Mapping[str, object],
) -> int | None:
    return (
        get_positive_int_value(progress_info.get("playlist_count"))
        or get_positive_int_value(progress_info.get("n_entries"))
        or get_positive_int_value(info_dict.get("playlist_count"))
        or get_positive_int_value(info_dict.get("n_entries"))
    )


def get_mapping_value(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value

    return {}


def get_non_empty_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    normalized_value = value.strip()

    if not normalized_value:
        return None

    return normalized_value


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


def detect_primary_output_path(
    *,
    download_dir: Path,
    existing_files: frozenset[Path],
) -> Path | None:
    created_files = collect_files(download_dir=download_dir) - existing_files
    completed_files = tuple(
        file_path
        for file_path in created_files
        if not is_temporary_download_file(file_path=file_path)
    )

    if not completed_files:
        return None

    return max(completed_files, key=get_output_file_sort_key)


def is_temporary_download_file(*, file_path: Path) -> bool:
    file_name = file_path.name.casefold()
    return file_name.endswith(TEMPORARY_DOWNLOAD_FILE_SUFFIXES)


def get_output_file_sort_key(file_path: Path) -> tuple[int, int, str]:
    try:
        stat_result = file_path.stat()
    except OSError:
        return (0, 0, str(file_path))

    return (stat_result.st_mtime_ns, stat_result.st_size, str(file_path))


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
