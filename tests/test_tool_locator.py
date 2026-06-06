from __future__ import annotations

from pathlib import Path

from yaloader.config.paths import AppPaths
from yaloader.infrastructure.system.tool_locator import (
    ToolLocatorProcessRunner,
    normalize_executable_name,
)


def test_normalize_executable_name_adds_windows_suffix() -> None:
    assert normalize_executable_name(executable_name="ffmpeg") == "ffmpeg.exe"


def test_normalize_executable_name_keeps_existing_windows_suffix() -> None:
    assert normalize_executable_name(executable_name="DENO.EXE") == "deno.exe"


def test_tool_locator_finds_app_managed_ffmpeg(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)
    paths.ffmpeg_executable.parent.mkdir(parents=True)
    paths.ffmpeg_executable.write_text("fake ffmpeg", encoding="utf-8")

    locator = ToolLocatorProcessRunner(paths=paths)

    assert locator.find_executable("ffmpeg") == paths.ffmpeg_executable


def test_tool_locator_finds_app_managed_deno(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)
    paths.deno_executable.parent.mkdir(parents=True)
    paths.deno_executable.write_text("fake deno", encoding="utf-8")

    locator = ToolLocatorProcessRunner(paths=paths)

    assert locator.find_executable("deno") == paths.deno_executable


def test_tool_locator_returns_none_for_missing_unknown_tool(tmp_path: Path) -> None:
    locator = ToolLocatorProcessRunner(paths=create_app_paths(tmp_path=tmp_path))

    assert locator.find_executable("definitely-missing-yaloader-tool") is None


def create_app_paths(tmp_path: Path) -> AppPaths:
    data_dir = tmp_path / "appdata"

    return AppPaths(
        data_dir=data_dir,
        downloads_dir=tmp_path / "downloads",
        logs_dir=data_dir / "logs",
        settings_file=data_dir / "settings.json",
        cookies_file=data_dir / "cookies.txt",
        history_file=data_dir / "download_history.json",
    )
