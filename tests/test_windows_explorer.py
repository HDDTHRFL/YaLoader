from __future__ import annotations

from pathlib import Path

from yaloader.infrastructure.windows.explorer import (
    WINDOWS_EXPLORER_EXECUTABLE,
    build_windows_explorer_directory_command,
    build_windows_explorer_file_select_command,
    resolve_existing_path,
)


def test_build_windows_explorer_file_select_command_quotes_path(tmp_path: Path) -> None:
    file_path = tmp_path / "Video With Spaces.mp4"
    file_path.write_text("video", encoding="utf-8")

    command = build_windows_explorer_file_select_command(file_path=file_path)

    assert command == f'{WINDOWS_EXPLORER_EXECUTABLE} /select,"{file_path.resolve()}"'


def test_build_windows_explorer_directory_command_quotes_path(tmp_path: Path) -> None:
    directory_path = tmp_path / "Directory With Spaces"
    directory_path.mkdir()

    command = build_windows_explorer_directory_command(directory_path=directory_path)

    assert command == f'{WINDOWS_EXPLORER_EXECUTABLE} "{directory_path.resolve()}"'


def test_resolve_existing_path_returns_file_when_file_exists(tmp_path: Path) -> None:
    file_path = tmp_path / "download.mp4"
    file_path.write_text("video", encoding="utf-8")

    resolved_path = resolve_existing_path(path=file_path)

    assert resolved_path == file_path


def test_resolve_existing_path_returns_parent_when_file_is_missing_but_parent_exists(
    tmp_path: Path,
) -> None:
    missing_file_path = tmp_path / "missing.mp4"

    resolved_path = resolve_existing_path(path=missing_file_path)

    assert resolved_path == tmp_path


def test_resolve_existing_path_returns_none_when_file_and_parent_are_missing(
    tmp_path: Path,
) -> None:
    missing_file_path = tmp_path / "missing-directory" / "missing.mp4"

    resolved_path = resolve_existing_path(path=missing_file_path)

    assert resolved_path is None
