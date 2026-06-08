from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from yaloader.application.dto.browser_cookies import (
    BrowserCookiesExportProgress,
    BrowserCookiesExportResult,
    BrowserId,
)
from yaloader.application.ports.browser_cookies_exporter import (
    BrowserCookiesExportProgressCallback,
)
from yaloader.ui.controllers.browser_cookies_controller import (
    BrowserCookiesController,
    BrowserCookiesControllerUpdate,
)


@dataclass(slots=True)
class FakeBrowserCookiesService:
    result: BrowserCookiesExportResult
    delay_seconds: float = 0.0
    calls: list[BrowserId] = field(default_factory=list, init=False)

    def export_from_browser(
        self,
        *,
        browser_id: BrowserId,
        progress_callback: BrowserCookiesExportProgressCallback | None = None,
    ) -> BrowserCookiesExportResult:
        self.calls.append(browser_id)

        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        if progress_callback is not None:
            progress_callback(
                BrowserCookiesExportProgress(
                    browser_id=browser_id,
                    message=f"{browser_id.value} progress",
                    percent=50,
                )
            )

        return self.result


def test_start_export_from_browser_runs_service() -> None:
    service = FakeBrowserCookiesService(
        result=BrowserCookiesExportResult.exported(
            browser_id=BrowserId.FIREFOX,
            cookies_file=Path("C:/AppData/yaloader/cookies.txt"),
        )
    )
    controller = BrowserCookiesController(service=service)

    try:
        start_update = controller.start_export_from_browser(browser_id=BrowserId.FIREFOX)
        finished_update = wait_for_finished_update(controller=controller)

        assert start_update.status_message == "Создание cookies.txt из firefox запущено"
        assert service.calls == [BrowserId.FIREFOX]
        assert finished_update.result is not None
        assert finished_update.result.is_success
        assert finished_update.status_message == "cookies.txt создан из firefox"
        assert finished_update.should_refresh_environment_status is True
    finally:
        controller.shutdown()


def test_poll_returns_progress_events() -> None:
    service = FakeBrowserCookiesService(
        result=BrowserCookiesExportResult.exported(
            browser_id=BrowserId.FIREFOX,
            cookies_file=Path("C:/AppData/yaloader/cookies.txt"),
        )
    )
    controller = BrowserCookiesController(service=service)

    try:
        controller.start_export_from_browser(browser_id=BrowserId.FIREFOX)
        finished_update = wait_for_finished_update(controller=controller)

        assert [event.browser_id for event in finished_update.progress_events] == [
            BrowserId.FIREFOX,
        ]
    finally:
        controller.shutdown()


def test_start_export_from_browser_rejects_parallel_run() -> None:
    service = FakeBrowserCookiesService(
        result=BrowserCookiesExportResult.exported(
            browser_id=BrowserId.FIREFOX,
            cookies_file=Path("C:/AppData/yaloader/cookies.txt"),
        ),
        delay_seconds=0.05,
    )
    controller = BrowserCookiesController(service=service)

    try:
        first_update = controller.start_export_from_browser(browser_id=BrowserId.FIREFOX)
        second_update = controller.start_export_from_browser(browser_id=BrowserId.FIREFOX)

        assert first_update.status_message == "Создание cookies.txt из firefox запущено"
        assert second_update.status_message == "Создание cookies.txt уже выполняется"
    finally:
        wait_for_finished_update(controller=controller)
        controller.shutdown()


def test_start_export_from_browser_reports_failed_result() -> None:
    service = FakeBrowserCookiesService(
        result=BrowserCookiesExportResult.failed(
            browser_id=BrowserId.FIREFOX,
            message="Не удалось создать cookies.txt из firefox",
        )
    )
    controller = BrowserCookiesController(service=service)

    try:
        controller.start_export_from_browser(browser_id=BrowserId.FIREFOX)
        finished_update = wait_for_finished_update(controller=controller)

        assert finished_update.result is not None
        assert not finished_update.result.is_success
        assert finished_update.status_message == "Не удалось создать cookies.txt из firefox"
        assert finished_update.should_refresh_environment_status is True
    finally:
        controller.shutdown()


def wait_for_finished_update(
    *,
    controller: BrowserCookiesController,
) -> BrowserCookiesControllerUpdate:
    deadline = time.monotonic() + 3.0
    progress_events: list[BrowserCookiesExportProgress] = []

    while time.monotonic() < deadline:
        update = controller.poll()
        progress_events.extend(update.progress_events)

        if update.result is not None or update.should_refresh_environment_status:
            return BrowserCookiesControllerUpdate(
                status_message=update.status_message,
                progress_events=tuple(progress_events),
                result=update.result,
                should_refresh_environment_status=update.should_refresh_environment_status,
            )

        time.sleep(0.01)

    raise AssertionError("Browser cookies export did not finish in time")
