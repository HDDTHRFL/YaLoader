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
    ToolUpdateCheckResult,
)
from yaloader.application.ports.tool_installer import ToolInstallationProgressCallback

TOOL_INSTALLATION_WORKERS_COUNT = 1
REQUIRED_TOOL_IDS: tuple[ToolId, ...] = (
    ToolId.FFMPEG,
    ToolId.DENO,
)
UPDATE_CHECK_TOOL_IDS: tuple[ToolId, ...] = (
    ToolId.FFMPEG,
    ToolId.DENO,
)
INSTALLABLE_UPDATE_TOOL_IDS: frozenset[ToolId] = frozenset(REQUIRED_TOOL_IDS)


class ToolInstallationUseCase(Protocol):
    def install_tool(
        self,
        *,
        tool_id: ToolId,
        progress_callback: ToolInstallationProgressCallback | None = None,
        force_reinstall: bool = False,
    ) -> ToolInstallationResult: ...

    def check_tool_updates(
        self,
        *,
        tool_ids: tuple[ToolId, ...],
    ) -> tuple[ToolUpdateCheckResult, ...]: ...


@dataclass(frozen=True, slots=True)
class ToolInstallationWorkerResult:
    results: tuple[ToolInstallationResult, ...] = ()
    update_checks: tuple[ToolUpdateCheckResult, ...] = ()
    force_reinstall: bool = False
    is_update_check: bool = False


@dataclass(frozen=True, slots=True)
class ToolInstallationControllerUpdate:
    status_message: str | None = None
    progress_events: tuple[ToolInstallationProgress, ...] = ()
    results: tuple[ToolInstallationResult, ...] = ()
    update_checks: tuple[ToolUpdateCheckResult, ...] = ()
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
            tool_ids=REQUIRED_TOOL_IDS,
            force_reinstall=False,
            start_message="Подготовка системы запущена",
            active_message="Подготовка системы уже выполняется",
        )

    def check_required_tools_updates(self) -> ToolInstallationControllerUpdate:
        if self.is_active:
            return ToolInstallationControllerUpdate(
                status_message="Подготовка или обновление системы уже выполняется",
            )

        self._active_future = self._executor.submit(
            self._check_updates_worker,
            UPDATE_CHECK_TOOL_IDS,
        )

        return ToolInstallationControllerUpdate(
            status_message="Проверяем обновления инструментов...",
        )

    def start_required_tools_update(
        self,
        *,
        tool_ids: tuple[ToolId, ...] = REQUIRED_TOOL_IDS,
        start_message: str = "Переустановка инструментов запущена",
    ) -> ToolInstallationControllerUpdate:
        return self._start_required_tools_operation(
            tool_ids=tool_ids,
            force_reinstall=True,
            start_message=start_message,
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

        if worker_result.is_update_check:
            return ToolInstallationControllerUpdate(
                status_message=build_tool_update_check_summary(
                    update_checks=worker_result.update_checks,
                ),
                progress_events=progress_events,
                update_checks=worker_result.update_checks,
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
        tool_ids: tuple[ToolId, ...],
        force_reinstall: bool,
        start_message: str,
        active_message: str,
    ) -> ToolInstallationControllerUpdate:
        if self.is_active:
            return ToolInstallationControllerUpdate(status_message=active_message)

        if not tool_ids:
            return ToolInstallationControllerUpdate(
                status_message="Нет инструментов для обновления",
            )

        self._active_future = self._executor.submit(
            self._install_tools_worker,
            tool_ids,
            force_reinstall,
        )

        return ToolInstallationControllerUpdate(status_message=start_message)

    def _check_updates_worker(
        self,
        tool_ids: tuple[ToolId, ...],
    ) -> ToolInstallationWorkerResult:
        return ToolInstallationWorkerResult(
            update_checks=self._service.check_tool_updates(tool_ids=tool_ids),
            is_update_check=True,
        )

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
        operation_title = "Переустановка инструментов" if force_reinstall else "Подготовка системы"
        return f"{operation_title} завершилось с ошибками: " + "; ".join(result.message for result in failed_results)

    if force_reinstall:
        return "Системные инструменты переустановлены"

    installed_results = tuple(result for result in results if result.status is ToolInstallationStatus.INSTALLED)

    if installed_results:
        return "Системные компоненты подготовлены"

    return "Системные компоненты уже доступны"


def build_tool_update_check_summary(
    *,
    update_checks: tuple[ToolUpdateCheckResult, ...],
) -> str:
    if not update_checks:
        return "Проверка обновлений не выполнялась"

    installable_update_checks = tuple(
        check for check in update_checks if check.should_update and is_installable_tool_update(tool_id=check.tool_id)
    )

    if installable_update_checks:
        return "Найдены обновления инструментов: " + "; ".join(
            format_tool_update_check_for_summary(check=check) for check in installable_update_checks
        )

    diagnostic_update_checks = tuple(
        check
        for check in update_checks
        if check.should_update and not is_installable_tool_update(tool_id=check.tool_id)
    )

    if diagnostic_update_checks:
        return "Найдены диагностические обновления: " + "; ".join(
            format_tool_update_check_for_summary(check=check) for check in diagnostic_update_checks
        )

    failed_checks = tuple(check for check in update_checks if not check.is_success)

    if failed_checks:
        return "Не удалось проверить часть инструментов: " + "; ".join(check.message for check in failed_checks)

    return "Доступных обновлений инструментов нет"


def is_installable_tool_update(*, tool_id: ToolId) -> bool:
    return tool_id in INSTALLABLE_UPDATE_TOOL_IDS


def format_tool_update_check_for_summary(*, check: ToolUpdateCheckResult) -> str:
    if check.current_version is None or check.latest_version is None:
        return check.message

    return f"{check.tool_id.value} {check.current_version} → {check.latest_version}"
