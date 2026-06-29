from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from yaloader.application.dto.tool_installation import (
    ToolId,
    ToolInstallationProgress,
    ToolInstallationResult,
    ToolUpdateCheckResult,
)
from yaloader.application.ports.tool_installer import ToolInstallationProgressCallback
from yaloader.ui.controllers.tool_installation_controller import (
    ToolInstallationController,
    ToolInstallationControllerUpdate,
    build_tool_installation_summary,
)


@dataclass(slots=True)
class FakeToolInstallationService:
    results_by_tool_id: dict[ToolId, ToolInstallationResult]
    update_checks: tuple[ToolUpdateCheckResult, ...] = ()
    delay_seconds: float = 0.0
    calls: list[ToolId] = field(default_factory=list, init=False)
    force_reinstall_values: list[bool] = field(default_factory=list, init=False)
    update_tool_id_requests: list[tuple[ToolId, ...]] = field(default_factory=list, init=False)

    def install_tool(
        self,
        *,
        tool_id: ToolId,
        progress_callback: ToolInstallationProgressCallback | None = None,
        force_reinstall: bool = False,
    ) -> ToolInstallationResult:
        self.calls.append(tool_id)
        self.force_reinstall_values.append(force_reinstall)

        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        if progress_callback is not None:
            progress_callback(
                ToolInstallationProgress(
                    tool_id=tool_id,
                    message=f"{tool_id.value} progress",
                    percent=50,
                )
            )

        return self.results_by_tool_id[tool_id]

    def check_tool_updates(
        self,
        *,
        tool_ids: tuple[ToolId, ...],
    ) -> tuple[ToolUpdateCheckResult, ...]:
        self.update_tool_id_requests.append(tool_ids)
        return tuple(check for check in self.update_checks if check.tool_id in tool_ids)


def test_start_required_tools_installation_runs_ffmpeg_and_deno() -> None:
    service = FakeToolInstallationService(
        results_by_tool_id={
            ToolId.FFMPEG: ToolInstallationResult.installed(
                tool_id=ToolId.FFMPEG,
                executable_path=Path("C:/AppData/yaloader/tools/ffmpeg/bin/ffmpeg.exe"),
            ),
            ToolId.DENO: ToolInstallationResult.installed(
                tool_id=ToolId.DENO,
                executable_path=Path("C:/AppData/yaloader/tools/deno/deno.exe"),
            ),
        }
    )
    controller = ToolInstallationController(service=service)

    try:
        start_update = controller.start_required_tools_installation()
        finished_update = wait_for_finished_update(controller=controller)

        assert start_update.status_message == "Подготовка системы запущена"
        assert service.calls == [ToolId.FFMPEG, ToolId.DENO]
        assert service.force_reinstall_values == [False, False]
        assert len(finished_update.results) == 2
        assert finished_update.status_message == "Системные компоненты подготовлены"
        assert finished_update.should_refresh_environment_status is True
    finally:
        controller.shutdown()


def test_check_required_tools_updates_returns_update_checks() -> None:
    service = FakeToolInstallationService(
        results_by_tool_id={},
        update_checks=(
            ToolUpdateCheckResult.update_available(
                tool_id=ToolId.FFMPEG,
                current_version="7.0",
                latest_version="8.0",
                executable_path=Path("C:/Tools/ffmpeg.exe"),
            ),
        ),
    )
    controller = ToolInstallationController(service=service)

    try:
        start_update = controller.check_required_tools_updates()
        finished_update = wait_for_finished_update(controller=controller)

        assert start_update.status_message == "Проверяем обновления инструментов..."
        assert service.update_tool_id_requests == [(ToolId.FFMPEG, ToolId.DENO)]
        assert finished_update.update_checks == service.update_checks
        assert finished_update.status_message == "Найдены обновления инструментов: ffmpeg 7.0 → 8.0"
    finally:
        controller.shutdown()


def test_start_required_tools_update_runs_ffmpeg_and_deno_with_force_reinstall() -> None:
    service = FakeToolInstallationService(
        results_by_tool_id={
            ToolId.FFMPEG: ToolInstallationResult.installed(
                tool_id=ToolId.FFMPEG,
                executable_path=Path("C:/AppData/yaloader/tools/ffmpeg/bin/ffmpeg.exe"),
            ),
            ToolId.DENO: ToolInstallationResult.installed(
                tool_id=ToolId.DENO,
                executable_path=Path("C:/AppData/yaloader/tools/deno/deno.exe"),
            ),
        }
    )
    controller = ToolInstallationController(service=service)

    try:
        start_update = controller.start_required_tools_update()
        finished_update = wait_for_finished_update(controller=controller)

        assert start_update.status_message == "Переустановка инструментов запущена"
        assert service.calls == [ToolId.FFMPEG, ToolId.DENO]
        assert service.force_reinstall_values == [True, True]
        assert len(finished_update.results) == 2
        assert finished_update.status_message == "Системные инструменты переустановлены"
        assert finished_update.should_refresh_environment_status is True
    finally:
        controller.shutdown()


def test_start_required_tools_update_accepts_custom_start_message() -> None:
    service = FakeToolInstallationService(
        results_by_tool_id={
            ToolId.FFMPEG: ToolInstallationResult.installed(
                tool_id=ToolId.FFMPEG,
                executable_path=Path("C:/AppData/yaloader/tools/ffmpeg/bin/ffmpeg.exe"),
            ),
            ToolId.DENO: ToolInstallationResult.installed(
                tool_id=ToolId.DENO,
                executable_path=Path("C:/AppData/yaloader/tools/deno/deno.exe"),
            ),
        }
    )
    controller = ToolInstallationController(service=service)

    try:
        start_update = controller.start_required_tools_update(
            start_message="Обновление инструментов запущено",
        )

        assert start_update.status_message == "Обновление инструментов запущено"
    finally:
        wait_for_finished_update(controller=controller)
        controller.shutdown()


def test_poll_returns_progress_events() -> None:
    service = FakeToolInstallationService(
        results_by_tool_id={
            ToolId.FFMPEG: ToolInstallationResult.available(
                tool_id=ToolId.FFMPEG,
                executable_path=Path("C:/Tools/ffmpeg.exe"),
            ),
            ToolId.DENO: ToolInstallationResult.available(
                tool_id=ToolId.DENO,
                executable_path=Path("C:/Tools/deno.exe"),
            ),
        }
    )
    controller = ToolInstallationController(service=service)

    try:
        controller.start_required_tools_installation()
        finished_update = wait_for_finished_update(controller=controller)

        assert [event.tool_id for event in finished_update.progress_events] == [
            ToolId.FFMPEG,
            ToolId.DENO,
        ]
    finally:
        controller.shutdown()


def test_start_required_tools_installation_rejects_parallel_run() -> None:
    service = FakeToolInstallationService(
        results_by_tool_id={
            ToolId.FFMPEG: ToolInstallationResult.available(
                tool_id=ToolId.FFMPEG,
                executable_path=Path("C:/Tools/ffmpeg.exe"),
            ),
            ToolId.DENO: ToolInstallationResult.available(
                tool_id=ToolId.DENO,
                executable_path=Path("C:/Tools/deno.exe"),
            ),
        },
        delay_seconds=0.05,
    )
    controller = ToolInstallationController(service=service)

    try:
        first_update = controller.start_required_tools_installation()
        second_update = controller.start_required_tools_update()

        assert first_update.status_message == "Подготовка системы запущена"
        assert second_update.status_message == "Подготовка или обновление системы уже выполняется"
    finally:
        wait_for_finished_update(controller=controller)
        controller.shutdown()


def test_build_tool_installation_summary_reports_failures() -> None:
    summary = build_tool_installation_summary(
        results=(
            ToolInstallationResult.failed(
                tool_id=ToolId.FFMPEG,
                message="Не удалось установить FFmpeg",
            ),
            ToolInstallationResult.installed(
                tool_id=ToolId.DENO,
                executable_path=Path("C:/AppData/yaloader/tools/deno/deno.exe"),
            ),
        )
    )

    assert summary == "Подготовка системы завершилось с ошибками: Не удалось установить FFmpeg"


def test_build_tool_installation_summary_reports_update_failures() -> None:
    summary = build_tool_installation_summary(
        results=(
            ToolInstallationResult.failed(
                tool_id=ToolId.FFMPEG,
                message="Не удалось обновить FFmpeg",
            ),
        ),
        force_reinstall=True,
    )

    assert (
        summary == "Переустановка инструментов завершилось с ошибками: Не удалось обновить FFmpeg"
    )


def test_build_tool_installation_summary_reports_already_available_tools() -> None:
    summary = build_tool_installation_summary(
        results=(
            ToolInstallationResult.available(
                tool_id=ToolId.FFMPEG,
                executable_path=Path("C:/Tools/ffmpeg.exe"),
            ),
            ToolInstallationResult.available(
                tool_id=ToolId.DENO,
                executable_path=Path("C:/Tools/deno.exe"),
            ),
        )
    )

    assert summary == "Системные компоненты уже доступны"


def wait_for_finished_update(
    *,
    controller: ToolInstallationController,
) -> ToolInstallationControllerUpdate:
    deadline = time.monotonic() + 3.0
    progress_events: list[ToolInstallationProgress] = []

    while time.monotonic() < deadline:
        update = controller.poll()
        progress_events.extend(update.progress_events)

        if update.results or update.update_checks or update.should_refresh_environment_status:
            return ToolInstallationControllerUpdate(
                status_message=update.status_message,
                progress_events=tuple(progress_events),
                results=update.results,
                update_checks=update.update_checks,
                should_refresh_environment_status=update.should_refresh_environment_status,
            )

        time.sleep(0.01)

    raise AssertionError("Tool installation did not finish in time")
