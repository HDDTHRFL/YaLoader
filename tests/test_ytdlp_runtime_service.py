from __future__ import annotations

from dataclasses import dataclass

from yaloader.application.dto.tool_installation import ToolId
from yaloader.application.dto.ytdlp_runtime import YtDlpRuntimeInfo
from yaloader.application.dto.ytdlp_runtime_update import YtDlpRuntimeUpdateResult
from yaloader.application.ports.ytdlp_runtime_installer import (
    YtDlpRuntimeUpdateProgressCallback,
)
from yaloader.application.services.ytdlp_runtime_service import YtDlpRuntimeService


@dataclass(slots=True)
class FakeYtDlpRuntimeProvider:
    runtime_info: YtDlpRuntimeInfo

    def get_runtime_info(self) -> YtDlpRuntimeInfo:
        return self.runtime_info


@dataclass(slots=True)
class FakeYtDlpRuntimeResetter:
    removed: bool

    def reset_external_runtime(self) -> bool:
        return self.removed


@dataclass(slots=True)
class FakeToolVersionChecker:
    current_version: str
    latest_version: str

    @property
    def tool_id(self) -> ToolId:
        return ToolId.YTDLP

    def get_current_version(self) -> str:
        return self.current_version

    def get_latest_version(self) -> str:
        return self.latest_version


@dataclass(slots=True)
class FakeYtDlpRuntimeInstaller:
    result: YtDlpRuntimeUpdateResult

    def install_latest(
        self,
        progress_callback: YtDlpRuntimeUpdateProgressCallback | None = None,
    ) -> YtDlpRuntimeUpdateResult:
        return self.result


def test_ytdlp_runtime_service_reports_available_update() -> None:
    service = create_service(
        current_version="2026.3.17",
        latest_version="2026.6.9",
    )

    result = service.check_update()

    assert result.should_update is True
    assert result.current_version == "2026.3.17"
    assert result.latest_version == "2026.6.9"


def test_ytdlp_runtime_service_reports_up_to_date_runtime() -> None:
    service = create_service(
        current_version="2026.6.9",
        latest_version="2026.6.9",
    )

    result = service.check_update()

    assert result.should_update is False
    assert result.is_success is True


def test_ytdlp_runtime_service_resets_external_runtime() -> None:
    runtime_info = YtDlpRuntimeInfo.bundled(version="2026.3.17")
    service = create_service(
        current_version="2026.6.9",
        latest_version="2026.6.9",
        runtime_info=runtime_info,
        removed=True,
    )

    result = service.reset_to_bundled()

    assert result.is_success is True
    assert result.message == "yt-dlp сброшен до встроенной версии 2026.3.17"


def create_service(
    *,
    current_version: str,
    latest_version: str,
    runtime_info: YtDlpRuntimeInfo | None = None,
    removed: bool = False,
) -> YtDlpRuntimeService:
    resolved_runtime_info = runtime_info or YtDlpRuntimeInfo.bundled(
        version=current_version,
    )
    return YtDlpRuntimeService(
        runtime_provider=FakeYtDlpRuntimeProvider(runtime_info=resolved_runtime_info),
        runtime_resetter=FakeYtDlpRuntimeResetter(removed=removed),
        version_checker=FakeToolVersionChecker(
            current_version=current_version,
            latest_version=latest_version,
        ),
        installer=FakeYtDlpRuntimeInstaller(
            result=YtDlpRuntimeUpdateResult.installed(runtime_info=resolved_runtime_info),
        ),
    )
