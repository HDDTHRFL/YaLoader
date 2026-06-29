from __future__ import annotations

from dataclasses import dataclass

from yaloader.application.dto.tool_installation import ToolId, ToolUpdateCheckResult
from yaloader.application.dto.ytdlp_runtime_update import YtDlpRuntimeUpdateResult
from yaloader.application.ports.tool_version_checker import ToolVersionChecker
from yaloader.application.ports.ytdlp_runtime import (
    YtDlpRuntimeInfoProvider,
    YtDlpRuntimeResetter,
)
from yaloader.application.ports.ytdlp_runtime_installer import (
    YtDlpRuntimeInstaller,
    YtDlpRuntimeUpdateProgressCallback,
)
from yaloader.infrastructure.tools.version_detection import is_version_newer


@dataclass(frozen=True, slots=True)
class YtDlpRuntimeService:
    runtime_provider: YtDlpRuntimeInfoProvider
    runtime_resetter: YtDlpRuntimeResetter
    version_checker: ToolVersionChecker
    installer: YtDlpRuntimeInstaller

    def check_update(self) -> ToolUpdateCheckResult:
        try:
            current_version = self.version_checker.get_current_version()
            latest_version = self.version_checker.get_latest_version()
        except Exception as error:
            return ToolUpdateCheckResult.check_failed(
                tool_id=ToolId.YTDLP,
                message=f"yt-dlp: не удалось проверить обновление: {error}",
            )

        if is_version_newer(
            candidate_version=latest_version,
            current_version=current_version,
        ):
            return ToolUpdateCheckResult.update_available(
                tool_id=ToolId.YTDLP,
                current_version=current_version,
                latest_version=latest_version,
            )

        return ToolUpdateCheckResult.up_to_date(
            tool_id=ToolId.YTDLP,
            current_version=current_version,
            latest_version=latest_version,
        )

    def install_latest(
        self,
        *,
        progress_callback: YtDlpRuntimeUpdateProgressCallback | None = None,
    ) -> YtDlpRuntimeUpdateResult:
        return self.installer.install_latest(progress_callback=progress_callback)

    def reset_to_bundled(self) -> YtDlpRuntimeUpdateResult:
        try:
            removed = self.runtime_resetter.reset_external_runtime()
            runtime_info = self.runtime_provider.get_runtime_info()
        except Exception as error:
            return YtDlpRuntimeUpdateResult.failed(
                message=f"Не удалось сбросить yt-dlp: {error}",
            )

        if removed:
            return YtDlpRuntimeUpdateResult.reset(runtime_info=runtime_info)

        return YtDlpRuntimeUpdateResult.not_installed(runtime_info=runtime_info)
