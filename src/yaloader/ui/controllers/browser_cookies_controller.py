from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from queue import Empty, SimpleQueue
from typing import Protocol

from yaloader.application.dto.browser_cookies import (
    BrowserCookiesExportProgress,
    BrowserCookiesExportResult,
    BrowserId,
)
from yaloader.application.ports.browser_cookies_exporter import (
    BrowserCookiesExportProgressCallback,
)

BROWSER_COOKIES_EXPORT_WORKERS_COUNT = 1


class BrowserCookiesExportUseCase(Protocol):
    def export_from_browser(
        self,
        *,
        browser_id: BrowserId,
        progress_callback: BrowserCookiesExportProgressCallback | None = None,
    ) -> BrowserCookiesExportResult: ...


@dataclass(frozen=True, slots=True)
class BrowserCookiesControllerUpdate:
    status_message: str | None = None
    progress_events: tuple[BrowserCookiesExportProgress, ...] = ()
    result: BrowserCookiesExportResult | None = None
    should_refresh_environment_status: bool = False


class BrowserCookiesController:
    def __init__(self, *, service: BrowserCookiesExportUseCase) -> None:
        self._service = service
        self._progress_events: SimpleQueue[BrowserCookiesExportProgress] = SimpleQueue()
        self._executor = ThreadPoolExecutor(
            max_workers=BROWSER_COOKIES_EXPORT_WORKERS_COUNT,
            thread_name_prefix="yaloader-browser-cookies",
        )
        self._active_future: Future[BrowserCookiesExportResult] | None = None

    @property
    def is_active(self) -> bool:
        return self._active_future is not None

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def start_export_from_browser(
        self,
        *,
        browser_id: BrowserId,
    ) -> BrowserCookiesControllerUpdate:
        if self.is_active:
            return BrowserCookiesControllerUpdate(
                status_message="Создание cookies.txt уже выполняется",
            )

        self._active_future = self._executor.submit(
            self._service.export_from_browser,
            browser_id=browser_id,
            progress_callback=self._handle_progress,
        )

        return BrowserCookiesControllerUpdate(
            status_message=f"Создание cookies.txt из {browser_id.value} запущено",
        )

    def poll(self) -> BrowserCookiesControllerUpdate:
        progress_events = self._drain_progress_events()

        if self._active_future is None:
            return BrowserCookiesControllerUpdate(progress_events=progress_events)

        if not self._active_future.done():
            return BrowserCookiesControllerUpdate(progress_events=progress_events)

        future = self._active_future
        self._active_future = None

        try:
            result = future.result()
        except Exception as error:
            return BrowserCookiesControllerUpdate(
                status_message=f"Создание cookies.txt завершилось ошибкой: {error}",
                progress_events=progress_events,
                should_refresh_environment_status=True,
            )

        return BrowserCookiesControllerUpdate(
            status_message=result.message,
            progress_events=progress_events,
            result=result,
            should_refresh_environment_status=True,
        )

    def _handle_progress(self, progress: BrowserCookiesExportProgress) -> None:
        self._progress_events.put(progress)

    def _drain_progress_events(self) -> tuple[BrowserCookiesExportProgress, ...]:
        progress_events: list[BrowserCookiesExportProgress] = []

        while True:
            try:
                progress_events.append(self._progress_events.get_nowait())
            except Empty:
                return tuple(progress_events)
