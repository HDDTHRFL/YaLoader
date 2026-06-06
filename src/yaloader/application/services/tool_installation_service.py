from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from yaloader.application.dto.tool_installation import (
    ToolId,
    ToolInstallationResult,
    build_tool_installation_progress,
)
from yaloader.application.ports.process_runner import ProcessRunner
from yaloader.application.ports.tool_installer import (
    ToolInstallationProgressCallback,
    ToolInstaller,
)

TOOL_EXECUTABLE_NAMES: Final[Mapping[ToolId, str]] = {
    ToolId.FFMPEG: "ffmpeg",
    ToolId.DENO: "deno",
}


@dataclass(frozen=True, slots=True)
class ToolInstallationService:
    process_runner: ProcessRunner
    installers: Mapping[ToolId, ToolInstaller]

    def check_tool(self, *, tool_id: ToolId) -> ToolInstallationResult:
        executable_path = self.process_runner.find_executable(
            self._get_executable_name(tool_id=tool_id),
        )

        if executable_path is None:
            return ToolInstallationResult.missing(tool_id=tool_id)

        return ToolInstallationResult.available(
            tool_id=tool_id,
            executable_path=executable_path,
        )

    def install_tool(
        self,
        *,
        tool_id: ToolId,
        progress_callback: ToolInstallationProgressCallback | None = None,
    ) -> ToolInstallationResult:
        current_result = self.check_tool(tool_id=tool_id)

        if current_result.is_success:
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
            message=f"Начинаем установку {tool_id.value}",
            percent=0,
        )

        result = installer.install(progress_callback=progress_callback)

        if result.is_success:
            self._emit_progress(
                progress_callback=progress_callback,
                tool_id=tool_id,
                message=result.message,
                percent=100,
                path=result.executable_path,
            )

        return result

    def _get_executable_name(self, *, tool_id: ToolId) -> str:
        return TOOL_EXECUTABLE_NAMES[tool_id]

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
