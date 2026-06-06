from __future__ import annotations

from pathlib import Path

from yaloader.infrastructure.system.tool_locator import (
    ToolLocatorProcessRunner,
    ToolSearchPaths,
    normalize_executable_name,
)


def test_normalize_executable_name_adds_windows_suffix() -> None:
    assert normalize_executable_name(executable_name="ffmpeg") == "ffmpeg.exe"


def test_normalize_executable_name_keeps_existing_windows_suffix() -> None:
    assert normalize_executable_name(executable_name="DENO.EXE") == "deno.exe"


def test_tool_locator_finds_app_managed_ffmpeg(tmp_path: Path) -> None:
    ffmpeg_executable = tmp_path / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
    ffmpeg_executable.parent.mkdir(parents=True)
    ffmpeg_executable.write_text("fake ffmpeg", encoding="utf-8")

    locator = ToolLocatorProcessRunner(
        search_paths=ToolSearchPaths(app_tools_dir=tmp_path / "tools"),
    )

    assert locator.find_executable("ffmpeg") == ffmpeg_executable


def test_tool_locator_finds_app_managed_deno(tmp_path: Path) -> None:
    deno_executable = tmp_path / "tools" / "deno" / "deno.exe"
    deno_executable.parent.mkdir(parents=True)
    deno_executable.write_text("fake deno", encoding="utf-8")

    locator = ToolLocatorProcessRunner(
        search_paths=ToolSearchPaths(app_tools_dir=tmp_path / "tools"),
    )

    assert locator.find_executable("deno") == deno_executable


def test_tool_locator_returns_none_for_missing_unknown_tool(tmp_path: Path) -> None:
    locator = ToolLocatorProcessRunner(
        search_paths=ToolSearchPaths(app_tools_dir=tmp_path / "tools"),
    )

    assert locator.find_executable("definitely-missing-yaloader-tool") is None
