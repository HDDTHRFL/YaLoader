from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from yaloader.application.dto.tool_installation import (
    ToolId,
    ToolInstallationProgress,
    ToolInstallationResult,
    ToolInstallationStatus,
)
from yaloader.application.ports.tool_installer import ToolInstallationProgressCallback
from yaloader.application.services.tool_installation_service import ToolInstallationService


@dataclass(slots=True)
class FakeProcessRunner:
    executables: dict[str, Path]

    def find_executable(self, executable_name: str) -> Path | None:
        return self.executables.get(executable_name)


@dataclass(slots=True)
class FakeToolInstaller:
    tool_id: ToolId
    result: ToolInstallationResult
    install_calls: int = 0
    force_reinstall_values: list[bool] = field(default_factory=list)
    progress_events: list[ToolInstallationProgress] = field(default_factory=list)

    def install(
        self,
        progress_callback: ToolInstallationProgressCallback | None = None,
        force_reinstall: bool = False,
    ) -> ToolInstallationResult:
        self.install_calls += 1
        self.force_reinstall_values.append(force_reinstall)

        if progress_callback is not None:
            progress = ToolInstallationProgress(
                tool_id=self.tool_id,
                message="fake install progress",
                percent=50,
            )
            self.progress_events.append(progress)
            progress_callback(progress)

        return self.result


def test_check_tool_returns_available_when_executable_is_found() -> None:
    ffmpeg_path = Path("C:/Tools/ffmpeg.exe")
    service = ToolInstallationService(
        process_runner=FakeProcessRunner(executables={"ffmpeg": ffmpeg_path}),
        installers={},
    )

    result = service.check_tool(tool_id=ToolId.FFMPEG)

    assert result.status is ToolInstallationStatus.AVAILABLE
    assert result.executable_path == ffmpeg_path
    assert result.is_success is True


def test_check_tool_returns_missing_when_executable_is_not_found() -> None:
    service = ToolInstallationService(
        process_runner=FakeProcessRunner(executables={}),
        installers={},
    )

    result = service.check_tool(tool_id=ToolId.DENO)

    assert result.status is ToolInstallationStatus.MISSING
    assert result.executable_path is None
    assert result.is_success is False


def test_install_tool_skips_installer_when_tool_is_already_available() -> None:
    ffmpeg_path = Path("C:/Tools/ffmpeg.exe")
    installer = FakeToolInstaller(
        tool_id=ToolId.FFMPEG,
        result=ToolInstallationResult.installed(
            tool_id=ToolId.FFMPEG,
            executable_path=Path("C:/App/ffmpeg.exe"),
        ),
    )
    service = ToolInstallationService(
        process_runner=FakeProcessRunner(executables={"ffmpeg": ffmpeg_path}),
        installers={ToolId.FFMPEG: installer},
    )

    result = service.install_tool(tool_id=ToolId.FFMPEG)

    assert result.status is ToolInstallationStatus.AVAILABLE
    assert result.executable_path == ffmpeg_path
    assert installer.install_calls == 0


def test_install_tool_force_reinstall_uses_installer_when_tool_is_already_available() -> None:
    ffmpeg_path = Path("C:/Tools/ffmpeg.exe")
    app_ffmpeg_path = Path("C:/App/ffmpeg.exe")
    installer = FakeToolInstaller(
        tool_id=ToolId.FFMPEG,
        result=ToolInstallationResult.installed(
            tool_id=ToolId.FFMPEG,
            executable_path=app_ffmpeg_path,
        ),
    )
    progress_events: list[ToolInstallationProgress] = []
    service = ToolInstallationService(
        process_runner=FakeProcessRunner(executables={"ffmpeg": ffmpeg_path}),
        installers={ToolId.FFMPEG: installer},
    )

    result = service.install_tool(
        tool_id=ToolId.FFMPEG,
        progress_callback=progress_events.append,
        force_reinstall=True,
    )

    assert result.status is ToolInstallationStatus.INSTALLED
    assert result.executable_path == app_ffmpeg_path
    assert installer.install_calls == 1
    assert installer.force_reinstall_values == [True]
    assert len(progress_events) == 3
    assert progress_events[0].message == "Начинаем обновление ffmpeg"
    assert progress_events[0].percent == 0
    assert progress_events[-1].percent == 100


def test_install_tool_returns_not_configured_when_installer_is_missing() -> None:
    progress_events: list[ToolInstallationProgress] = []
    service = ToolInstallationService(
        process_runner=FakeProcessRunner(executables={}),
        installers={},
    )

    result = service.install_tool(
        tool_id=ToolId.FFMPEG,
        progress_callback=progress_events.append,
    )

    assert result.status is ToolInstallationStatus.NOT_CONFIGURED
    assert result.is_success is False
    assert len(progress_events) == 1
    assert progress_events[0].tool_id is ToolId.FFMPEG
    assert progress_events[0].percent == 0


def test_install_tool_uses_registered_installer_when_tool_is_missing() -> None:
    deno_path = Path("C:/AppData/yaloader/tools/deno/deno.exe")
    installer = FakeToolInstaller(
        tool_id=ToolId.DENO,
        result=ToolInstallationResult.installed(
            tool_id=ToolId.DENO,
            executable_path=deno_path,
        ),
    )
    progress_events: list[ToolInstallationProgress] = []
    service = ToolInstallationService(
        process_runner=FakeProcessRunner(executables={}),
        installers={ToolId.DENO: installer},
    )

    result = service.install_tool(
        tool_id=ToolId.DENO,
        progress_callback=progress_events.append,
    )

    assert result.status is ToolInstallationStatus.INSTALLED
    assert result.executable_path == deno_path
    assert installer.install_calls == 1
    assert installer.force_reinstall_values == [False]
    assert len(progress_events) == 3
    assert progress_events[0].percent == 0
    assert progress_events[1].percent == 50
    assert progress_events[2].percent == 100


def test_install_tool_returns_failed_result_from_installer() -> None:
    installer = FakeToolInstaller(
        tool_id=ToolId.FFMPEG,
        result=ToolInstallationResult.failed(
            tool_id=ToolId.FFMPEG,
            message="download failed",
        ),
    )
    service = ToolInstallationService(
        process_runner=FakeProcessRunner(executables={}),
        installers={ToolId.FFMPEG: installer},
    )

    result = service.install_tool(tool_id=ToolId.FFMPEG)

    assert result.status is ToolInstallationStatus.FAILED
    assert result.message == "download failed"
    assert result.is_success is False
    assert installer.install_calls == 1
