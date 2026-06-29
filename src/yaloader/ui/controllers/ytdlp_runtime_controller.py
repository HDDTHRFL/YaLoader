from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from queue import Empty, SimpleQueue
from typing import Protocol

from yaloader.application.dto.tool_installation import ToolUpdateCheckResult
from yaloader.application.dto.ytdlp_runtime_update import (
    YtDlpRuntimeUpdateProgress,
    YtDlpRuntimeUpdateResult,
)
from yaloader.application.ports.ytdlp_runtime_installer import (
    YtDlpRuntimeUpdateProgressCallback,
)

YTDLP_RUNTIME_WORKERS_COUNT = 1


class YtDlpRuntimeUseCase(Protocol):
    def check_update(self) -> ToolUpdateCheckResult: ...

    def install_latest(
        self,
        *,
        progress_callback: YtDlpRuntimeUpdateProgressCallback | None = None,
    ) -> YtDlpRuntimeUpdateResult: ...

    def reset_to_bundled(self) -> YtDlpRuntimeUpdateResult: ...


@dataclass(frozen=True, slots=True)
class YtDlpRuntimeWorkerResult:
    update_check: ToolUpdateCheckResult | None = None
    result: YtDlpRuntimeUpdateResult | None = None


@dataclass(frozen=True, slots=True)
class YtDlpRuntimeControllerUpdate:
    status_message: str | None = None
    progress_events: tuple[YtDlpRuntimeUpdateProgress, ...] = ()
    update_check: ToolUpdateCheckResult | None = None
    result: YtDlpRuntimeUpdateResult | None = None
    should_refresh_environment_status: bool = False


class YtDlpRuntimeController:
    def __init__(self, *, service: YtDlpRuntimeUseCase) -> None:
        self._service = service
        self._progress_events: SimpleQueue[YtDlpRuntimeUpdateProgress] = SimpleQueue()
        self._executor = ThreadPoolExecutor(
            max_workers=YTDLP_RUNTIME_WORKERS_COUNT,
            thread_name_prefix="yaloader-ytdlp-runtime",
        )
        self._active_future: Future[YtDlpRuntimeWorkerResult] | None = None

    @property
    def is_active(self) -> bool:
        return self._active_future is not None

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def check_update(self) -> YtDlpRuntimeControllerUpdate:
        if self.is_active:
            return YtDlpRuntimeControllerUpdate(
                status_message="Операция с yt-dlp уже выполняется",
            )

        self._active_future = self._executor.submit(self._check_update_worker)

        return YtDlpRuntimeControllerUpdate(
            status_message="Проверяем обновление yt-dlp...",
        )

    def install_latest(self) -> YtDlpRuntimeControllerUpdate:
        if self.is_active:
            return YtDlpRuntimeControllerUpdate(
                status_message="Операция с yt-dlp уже выполняется",
            )

        self._active_future = self._executor.submit(self._install_latest_worker)

        return YtDlpRuntimeControllerUpdate(
            status_message="Обновление yt-dlp запущено",
        )

    def reset_to_bundled(self) -> YtDlpRuntimeControllerUpdate:
        if self.is_active:
            return YtDlpRuntimeControllerUpdate(
                status_message="Операция с yt-dlp уже выполняется",
            )

        self._active_future = self._executor.submit(self._reset_to_bundled_worker)

        return YtDlpRuntimeControllerUpdate(
            status_message="Сброс yt-dlp запущен",
        )

    def poll(self) -> YtDlpRuntimeControllerUpdate:
        progress_events = self._drain_progress_events()

        if self._active_future is None:
            return YtDlpRuntimeControllerUpdate(progress_events=progress_events)

        if not self._active_future.done():
            return YtDlpRuntimeControllerUpdate(progress_events=progress_events)

        future = self._active_future
        self._active_future = None

        try:
            worker_result = future.result()
        except Exception as error:
            return YtDlpRuntimeControllerUpdate(
                status_message=f"Операция с yt-dlp завершилась ошибкой: {error}",
                progress_events=progress_events,
                should_refresh_environment_status=True,
            )

        if worker_result.update_check is not None:
            return YtDlpRuntimeControllerUpdate(
                status_message=build_ytdlp_update_check_summary(
                    update_check=worker_result.update_check,
                ),
                progress_events=progress_events,
                update_check=worker_result.update_check,
            )

        if worker_result.result is not None:
            return YtDlpRuntimeControllerUpdate(
                status_message=worker_result.result.message,
                progress_events=progress_events,
                result=worker_result.result,
                should_refresh_environment_status=True,
            )

        return YtDlpRuntimeControllerUpdate(
            status_message="Операция с yt-dlp не вернула результат",
            progress_events=progress_events,
            should_refresh_environment_status=True,
        )

    def _check_update_worker(self) -> YtDlpRuntimeWorkerResult:
        return YtDlpRuntimeWorkerResult(update_check=self._service.check_update())

    def _install_latest_worker(self) -> YtDlpRuntimeWorkerResult:
        return YtDlpRuntimeWorkerResult(
            result=self._service.install_latest(progress_callback=self._handle_progress),
        )

    def _reset_to_bundled_worker(self) -> YtDlpRuntimeWorkerResult:
        return YtDlpRuntimeWorkerResult(result=self._service.reset_to_bundled())

    def _handle_progress(self, progress: YtDlpRuntimeUpdateProgress) -> None:
        self._progress_events.put(progress)

    def _drain_progress_events(self) -> tuple[YtDlpRuntimeUpdateProgress, ...]:
        progress_events: list[YtDlpRuntimeUpdateProgress] = []

        while True:
            try:
                progress_events.append(self._progress_events.get_nowait())
            except Empty:
                return tuple(progress_events)


def build_ytdlp_update_check_summary(*, update_check: ToolUpdateCheckResult) -> str:
    if not update_check.is_success:
        return update_check.message

    if update_check.should_update and update_check.latest_version is not None:
        return f"yt-dlp: доступна версия {update_check.latest_version}"

    if update_check.current_version is not None:
        return f"yt-dlp: актуальная версия {update_check.current_version}"

    return update_check.message
