from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from yaloader.application.dto.tool_installation import (
    ToolId,
    ToolInstallationResult,
    ToolInstallationStatus,
    ToolUpdateCheckResult,
    build_tool_installation_progress,
)
from yaloader.application.ports.process_runner import ProcessRunner
from yaloader.application.ports.tool_installer import (
    ToolInstallationProgressCallback,
    ToolInstaller,
)
from yaloader.application.ports.tool_version_checker import ToolVersionChecker
from yaloader.infrastructure.tools.version_detection import is_version_newer

TOOL_EXECUTABLE_NAMES: Final[Mapping[ToolId, str]] = {
    ToolId.FFMPEG: "ffmpeg",
    ToolId.DENO: "deno",
}


def build_empty_tool_version_checkers() -> Mapping[ToolId, ToolVersionChecker]:
    return {}


@dataclass(frozen=True, slots=True)
class ToolInstallationService:
    process_runner: ProcessRunner
    installers: Mapping[ToolId, ToolInstaller]
    version_checkers: Mapping[ToolId, ToolVersionChecker] = field(
        default_factory=build_empty_tool_version_checkers,
    )

    def check_tool(self, *, tool_id: ToolId) -> ToolInstallationResult:
        executable_name = TOOL_EXECUTABLE_NAMES.get(tool_id)

        if executable_name is None:
            return ToolInstallationResult.not_configured(tool_id=tool_id)

        executable_path = self.process_runner.find_executable(executable_name)

        if executable_path is None:
            return ToolInstallationResult.missing(tool_id=tool_id)

        return ToolInstallationResult.available(
            tool_id=tool_id,
            executable_path=executable_path,
        )

    def check_tool_update(self, *, tool_id: ToolId) -> ToolUpdateCheckResult:
        version_checker = self.version_checkers.get(tool_id)

        if version_checker is not None:
            return self._check_version_checker_update(version_checker=version_checker)

        current_result = self.check_tool(tool_id=tool_id)

        if current_result.status is ToolInstallationStatus.MISSING:
            return ToolUpdateCheckResult.missing(tool_id=tool_id)

        installer = self.installers.get(tool_id)

        if installer is None:
            return ToolUpdateCheckResult.check_failed(
                tool_id=tool_id,
                message=f"{tool_id.value}: проверка обновления не настроена",
                executable_path=current_result.executable_path,
            )

        if current_result.executable_path is None:
            return ToolUpdateCheckResult.check_failed(
                tool_id=tool_id,
                message=f"{tool_id.value}: не удалось определить путь к исполняемому файлу",
            )

        try:
            current_version = installer.get_installed_version(
                executable_path=current_result.executable_path,
            )
            latest_version = installer.get_latest_version()
        except Exception as error:
            return ToolUpdateCheckResult.check_failed(
                tool_id=tool_id,
                message=f"{tool_id.value}: не удалось проверить обновление: {error}",
                executable_path=current_result.executable_path,
            )

        if is_version_newer(
            candidate_version=latest_version,
            current_version=current_version,
        ):
            return ToolUpdateCheckResult.update_available(
                tool_id=tool_id,
                current_version=current_version,
                latest_version=latest_version,
                executable_path=current_result.executable_path,
            )

        return ToolUpdateCheckResult.up_to_date(
            tool_id=tool_id,
            current_version=current_version,
            latest_version=latest_version,
            executable_path=current_result.executable_path,
        )

    def check_tool_updates(
        self,
        *,
        tool_ids: tuple[ToolId, ...],
    ) -> tuple[ToolUpdateCheckResult, ...]:
        return tuple(self.check_tool_update(tool_id=tool_id) for tool_id in tool_ids)

    def install_tool(
        self,
        *,
        tool_id: ToolId,
        progress_callback: ToolInstallationProgressCallback | None = None,
        force_reinstall: bool = False,
    ) -> ToolInstallationResult:
        current_result = self.check_tool(tool_id=tool_id)

        if current_result.is_success and not force_reinstall:
            self._emit_progress(
                progress_callback=progress_callback,
                tool_id=tool_id,
                message=current_result.message,
                percent=100,
                path=current_result.executable_path,
            )
            return current_result

        installer = self.installers.get(tool_id)

        if installer is None:
            result = ToolInstallationResult.not_configured(tool_id=tool_id)
            self._emit_progress(
                progress_callback=progress_callback,
                tool_id=tool_id,
                message=result.message,
                percent=0,
            )
            return result

        self._emit_progress(
            progress_callback=progress_callback,
            tool_id=tool_id,
            message=build_tool_start_message(
                tool_id=tool_id,
                force_reinstall=force_reinstall,
            ),
            percent=0,
        )

        result = installer.install(
            progress_callback=progress_callback,
            force_reinstall=force_reinstall,
        )

        if result.is_success:
            self._emit_progress(
                progress_callback=progress_callback,
                tool_id=tool_id,
                message=result.message,
                percent=100,
                path=result.executable_path,
            )

        return result

    def _check_version_checker_update(
        self,
        *,
        version_checker: ToolVersionChecker,
    ) -> ToolUpdateCheckResult:
        tool_id = version_checker.tool_id

        try:
            current_version = version_checker.get_current_version()
            latest_version = version_checker.get_latest_version()
        except Exception as error:
            return ToolUpdateCheckResult.check_failed(
                tool_id=tool_id,
                message=f"{tool_id.value}: не удалось проверить обновление: {error}",
            )

        if is_version_newer(
            candidate_version=latest_version,
            current_version=current_version,
        ):
            return ToolUpdateCheckResult.update_available(
                tool_id=tool_id,
                current_version=current_version,
                latest_version=latest_version,
            )

        return ToolUpdateCheckResult.up_to_date(
            tool_id=tool_id,
            current_version=current_version,
            latest_version=latest_version,
        )

    def _emit_progress(
        self,
        *,
        progress_callback: ToolInstallationProgressCallback | None,
        tool_id: ToolId,
        message: str,
        percent: int | None = None,
        path: Path | None = None,
    ) -> None:
        if progress_callback is None:
            return

        progress_callback(
            build_tool_installation_progress(
                tool_id=tool_id,
                message=message,
                percent=percent,
                path=path,
            )
        )


def build_tool_start_message(
    *,
    tool_id: ToolId,
    force_reinstall: bool,
) -> str:
    if force_reinstall:
        return f"Начинаем переустановку {tool_id.value}"

    return f"Начинаем установку {tool_id.value}"
