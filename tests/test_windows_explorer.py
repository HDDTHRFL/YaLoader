from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from yaloader.infrastructure.windows import explorer
from yaloader.infrastructure.windows.explorer import (
    WINDOWS_EXPLORER_EXECUTABLE,
    activate_existing_explorer_directory_window,
    build_windows_explorer_directory_command,
    build_windows_explorer_file_select_command,
    resolve_existing_path,
)


@dataclass(slots=True)
class FakeShellFolderItem:
    Path: str


@dataclass(slots=True)
class FakeShellFolder:
    Self: FakeShellFolderItem

    def ParseName(self, name: str) -> object:  # noqa: N802
        return object()


@dataclass(slots=True)
class FakeShellFolderView:
    Folder: FakeShellFolder

    def SelectItem(self, item: object, flags: int) -> object:  # noqa: N802
        return object()


@dataclass(slots=True)
class FakeShellWindow:
    HWND: int
    Document: FakeShellFolderView


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


def test_activate_existing_explorer_directory_window_activates_matching_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory_path = tmp_path / "Downloads"
    directory_path.mkdir()
    shell_window = FakeShellWindow(
        HWND=123,
        Document=FakeShellFolderView(
            Folder=FakeShellFolder(
                Self=FakeShellFolderItem(Path=str(directory_path)),
            )
        ),
    )
    activated_hwnds: list[int] = []

    monkeypatch.setattr(
        explorer,
        "iter_windows_explorer_windows",
        lambda: (shell_window,),
    )
    monkeypatch.setattr(
        explorer,
        "activate_shell_window",
        lambda *, shell_window: activated_hwnds.append(shell_window.HWND),
    )

    result = activate_existing_explorer_directory_window(directory_path=directory_path)

    assert result is True
    assert activated_hwnds == [123]


def test_activate_existing_explorer_directory_window_returns_false_without_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_directory = tmp_path / "Target"
    other_directory = tmp_path / "Other"
    target_directory.mkdir()
    other_directory.mkdir()
    shell_window = FakeShellWindow(
        HWND=123,
        Document=FakeShellFolderView(
            Folder=FakeShellFolder(
                Self=FakeShellFolderItem(Path=str(other_directory)),
            )
        ),
    )

    monkeypatch.setattr(
        explorer,
        "iter_windows_explorer_windows",
        lambda: (shell_window,),
    )

    result = activate_existing_explorer_directory_window(directory_path=target_directory)

    assert result is False
