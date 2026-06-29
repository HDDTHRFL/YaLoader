from __future__ import annotations

from pathlib import Path

from yaloader.config.paths import AppPaths, ensure_app_directories


def test_app_paths_exposes_app_managed_tool_paths(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)

    assert paths.tools_dir == tmp_path / "appdata" / "tools"
    assert paths.ffmpeg_dir == tmp_path / "appdata" / "tools" / "ffmpeg"
    assert paths.ffmpeg_bin_dir == tmp_path / "appdata" / "tools" / "ffmpeg" / "bin"
    assert paths.ffmpeg_executable == (tmp_path / "appdata" / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe")
    assert paths.deno_dir == tmp_path / "appdata" / "tools" / "deno"
    assert paths.deno_executable == tmp_path / "appdata" / "tools" / "deno" / "deno.exe"


def test_required_directories_include_tools_dir(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)

    assert paths.tools_dir in paths.required_directories


def test_ensure_app_directories_creates_tools_dir(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)

    ensure_app_directories(paths=paths)

    assert paths.data_dir.is_dir()
    assert paths.downloads_dir.is_dir()
    assert paths.logs_dir.is_dir()
    assert paths.tools_dir.is_dir()


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
