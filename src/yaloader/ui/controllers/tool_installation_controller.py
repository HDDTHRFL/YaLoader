from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from queue import Empty, SimpleQueue
from typing import Protocol

from yaloader.application.dto.tool_installation import (
    ToolId,
    ToolInstallationProgress,
    ToolInstallationResult,
    ToolInstallationStatus,
)
from yaloader.application.ports.tool_installer import ToolInstallationProgressCallback

TOOL_INSTALLATION_WORKERS_COUNT = 1
REQUIRED_TOOL_IDS: tuple[ToolId, ...] = (
    ToolId.FFMPEG,
    ToolId.DENO,
)


class ToolInstallationUseCase(Protocol):
    def install_tool(
        self,
        *,
        tool_id: ToolId,
        progress_callback: ToolInstallationProgressCallback | None = None,
        force_reinstall: bool = False,
    ) -> ToolInstallationResult: ...


@dataclass(frozen=True, slots=True)
class ToolInstallationWorkerResult:
    results: tuple[ToolInstallationResult, ...]
    force_reinstall: bool


@dataclass(frozen=True, slots=True)
class ToolInstallationControllerUpdate:
    status_message: str | None = None
    progress_events: tuple[ToolInstallationProgress, ...] = ()
    results: tuple[ToolInstallationResult, ...] = ()
    should_refresh_environment_status: bool = False


class ToolInstallationController:
    def __init__(self, *, service: ToolInstallationUseCase) -> None:
        self._service = service
        self._progress_events: SimpleQueue[ToolInstallationProgress] = SimpleQueue()
        self._executor = ThreadPoolExecutor(
            max_workers=TOOL_INSTALLATION_WORKERS_COUNT,
            thread_name_prefix="yaloader-tool-install",
        )
        self._active_future: Future[ToolInstallationWorkerResult] | None = None

    @property
    def is_active(self) -> bool:
        return self._active_future is not None

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def start_required_tools_installation(self) -> ToolInstallationControllerUpdate:
        return self._start_required_tools_operation(
            force_reinstall=False,
            start_message="Подготовка системы запущена",
            active_message="Подготовка системы уже выполняется",
        )

    def start_required_tools_update(self) -> ToolInstallationControllerUpdate:
        return self._start_required_tools_operation(
            force_reinstall=True,
            start_message="Обновление инструментов запущено",
            active_message="Подготовка или обновление системы уже выполняется",
        )

    def poll(self) -> ToolInstallationControllerUpdate:
        progress_events = self._drain_progress_events()

        if self._active_future is None:
            return ToolInstallationControllerUpdate(progress_events=progress_events)

        if not self._active_future.done():
            return ToolInstallationControllerUpdate(progress_events=progress_events)

        future = self._active_future
        self._active_future = None

        try:
            worker_result = future.result()
        except Exception as error:
            return ToolInstallationControllerUpdate(
                status_message=f"Подготовка системы завершилась ошибкой: {error}",
                progress_events=progress_events,
                should_refresh_environment_status=True,
            )

        return ToolInstallationControllerUpdate(
            status_message=build_tool_installation_summary(
                results=worker_result.results,
                force_reinstall=worker_result.force_reinstall,
            ),
            progress_events=progress_events,
            results=worker_result.results,
            should_refresh_environment_status=True,
        )

    def _start_required_tools_operation(
        self,
        *,
        force_reinstall: bool,
        start_message: str,
        active_message: str,
    ) -> ToolInstallationControllerUpdate:
        if self.is_active:
            return ToolInstallationControllerUpdate(status_message=active_message)

        self._active_future = self._executor.submit(
            self._install_tools_worker,
            REQUIRED_TOOL_IDS,
            force_reinstall,
        )

        return ToolInstallationControllerUpdate(status_message=start_message)

    def _install_tools_worker(
        self,
        tool_ids: tuple[ToolId, ...],
        force_reinstall: bool,
    ) -> ToolInstallationWorkerResult:
        results: list[ToolInstallationResult] = []

        for tool_id in tool_ids:
            result = self._service.install_tool(
                tool_id=tool_id,
                progress_callback=self._handle_progress,
                force_reinstall=force_reinstall,
            )
            results.append(result)

        return ToolInstallationWorkerResult(
            results=tuple(results),
            force_reinstall=force_reinstall,
        )

    def _handle_progress(self, progress: ToolInstallationProgress) -> None:
        self._progress_events.put(progress)

    def _drain_progress_events(self) -> tuple[ToolInstallationProgress, ...]:
        progress_events: list[ToolInstallationProgress] = []

        while True:
            try:
                progress_events.append(self._progress_events.get_nowait())
            except Empty:
                return tuple(progress_events)


def build_tool_installation_summary(
    *,
    results: tuple[ToolInstallationResult, ...],
    force_reinstall: bool = False,
) -> str:
    if not results:
        return "Подготовка системы не выполнялась"

    failed_results = tuple(result for result in results if not result.is_success)

    if failed_results:
        operation_title = "Обновление инструментов" if force_reinstall else "Подготовка системы"
        return f"{operation_title} завершилось с ошибками: " + "; ".join(
            result.message for result in failed_results
        )

    if force_reinstall:
        return "Системные инструменты обновлены"

    installed_results = tuple(
        result for result in results if result.status is ToolInstallationStatus.INSTALLED
    )

    if installed_results:
        return "Системные компоненты подготовлены"

    return "Системные компоненты уже доступны"
