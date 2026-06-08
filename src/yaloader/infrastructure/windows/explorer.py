from __future__ import annotations

import importlib
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, cast

from loguru import logger

WINDOWS_PLATFORM_PREFIX = "win"
WINDOWS_EXPLORER_EXECUTABLE = "explorer.exe"

SVSI_SELECT = 0x0001
SVSI_DESELECTOTHERS = 0x0004
SVSI_ENSUREVISIBLE = 0x0008
SVSI_FOCUSED = 0x0010
SVSI_SELECT_FLAGS = SVSI_SELECT | SVSI_DESELECTOTHERS | SVSI_ENSUREVISIBLE | SVSI_FOCUSED

DEFAULT_SHOW_WINDOW_RESTORE = 9


class ShellFolderItem(Protocol):
    Path: str


class ShellFolder(Protocol):
    Self: ShellFolderItem

    def ParseName(self, name: str) -> object: ...  # noqa: N802


class ShellFolderView(Protocol):
    Folder: ShellFolder

    def SelectItem(self, item: object, flags: int) -> object: ...  # noqa: N802


class ShellWindow(Protocol):
    HWND: int
    Document: ShellFolderView


class ShellApplication(Protocol):
    def Windows(self) -> object: ...  # noqa: N802


def is_windows_platform() -> bool:
    return sys.platform.startswith(WINDOWS_PLATFORM_PREFIX)


def reveal_path_in_file_manager(path: Path) -> bool:
    existing_path = resolve_existing_path(path=path)

    if existing_path is None:
        return False

    if is_windows_platform():
        return reveal_path_in_windows_explorer(path=existing_path)

    return False


def resolve_existing_path(*, path: Path) -> Path | None:
    if path.exists():
        return path

    parent_path = path.parent

    if parent_path.exists():
        return parent_path

    return None


def reveal_path_in_windows_explorer(*, path: Path) -> bool:
    resolved_path = path.resolve()

    if resolved_path.is_file():
        if select_file_in_existing_explorer_window(file_path=resolved_path):
            return True

        return open_windows_explorer_with_file_selected(file_path=resolved_path)

    if activate_existing_explorer_directory_window(directory_path=resolved_path):
        return True

    return open_windows_explorer_directory(directory_path=resolved_path)


def activate_existing_explorer_directory_window(*, directory_path: Path) -> bool:
    target_directory = directory_path.resolve()

    for shell_window in iter_windows_explorer_windows():
        window_directory = get_shell_window_directory(shell_window=shell_window)

        if window_directory is None:
            continue

        if not is_same_windows_path(window_directory, target_directory):
            continue

        activate_shell_window(shell_window=shell_window)
        return True

    return False


def select_file_in_existing_explorer_window(*, file_path: Path) -> bool:
    target_directory = file_path.parent.resolve()

    for shell_window in iter_windows_explorer_windows():
        window_directory = get_shell_window_directory(shell_window=shell_window)

        if window_directory is None:
            continue

        if not is_same_windows_path(window_directory, target_directory):
            continue

        if not select_file_in_shell_window(
            shell_window=shell_window,
            file_path=file_path,
        ):
            continue

        activate_shell_window(shell_window=shell_window)
        return True

    return False


def iter_windows_explorer_windows() -> tuple[ShellWindow, ...]:
    try:
        win32com_client = importlib.import_module("win32com.client")
        dispatch = getattr(win32com_client, "Dispatch", None)

        if not callable(dispatch):
            return ()

        shell_application = cast(ShellApplication, dispatch("Shell.Application"))
        return tuple(cast(Iterable[ShellWindow], shell_application.Windows()))
    except Exception as error:
        logger.debug("Failed to enumerate Windows Explorer windows. error={}", error)
        return ()


def get_shell_window_directory(*, shell_window: ShellWindow) -> Path | None:
    try:
        folder_path = shell_window.Document.Folder.Self.Path
    except Exception:
        return None

    if not folder_path:
        return None

    try:
        return Path(folder_path).resolve()
    except OSError:
        return None


def select_file_in_shell_window(*, shell_window: ShellWindow, file_path: Path) -> bool:
    try:
        folder_item = shell_window.Document.Folder.ParseName(file_path.name)

        if folder_item is None:
            return False

        shell_window.Document.SelectItem(folder_item, SVSI_SELECT_FLAGS)
        return True
    except Exception as error:
        logger.debug(
            "Failed to select file in existing Explorer window. path={} error={}",
            file_path,
            error,
        )
        return False


def activate_shell_window(*, shell_window: ShellWindow) -> None:
    try:
        win32gui = importlib.import_module("win32gui")
        win32con = importlib.import_module("win32con")

        show_window = getattr(win32gui, "ShowWindow", None)
        set_foreground_window = getattr(win32gui, "SetForegroundWindow", None)
        restore_flag = getattr(win32con, "SW_RESTORE", DEFAULT_SHOW_WINDOW_RESTORE)

        if callable(show_window):
            show_window(shell_window.HWND, restore_flag)

        if callable(set_foreground_window):
            set_foreground_window(shell_window.HWND)
    except Exception as error:
        logger.debug(
            "Failed to activate existing Explorer window. hwnd={} error={}",
            shell_window.HWND,
            error,
        )


def open_windows_explorer_with_file_selected(*, file_path: Path) -> bool:
    command = build_windows_explorer_file_select_command(file_path=file_path)

    try:
        logger.debug("Opening Explorer with selected file. command={}", command)
        subprocess.Popen(command)
        return True
    except OSError as error:
        logger.debug(
            "Failed to open Explorer with file selected. path={} error={}",
            file_path,
            error,
        )
        return open_windows_explorer_directory(directory_path=file_path.parent)


def open_windows_explorer_directory(*, directory_path: Path) -> bool:
    command = build_windows_explorer_directory_command(directory_path=directory_path)

    try:
        logger.debug("Opening Explorer directory. command={}", command)
        subprocess.Popen(command)
        return True
    except OSError as error:
        logger.debug(
            "Failed to open Explorer directory. path={} error={}",
            directory_path,
            error,
        )
        return False


def build_windows_explorer_file_select_command(*, file_path: Path) -> str:
    return f'{WINDOWS_EXPLORER_EXECUTABLE} /select,"{file_path.resolve()}"'


def build_windows_explorer_directory_command(*, directory_path: Path) -> str:
    return f'{WINDOWS_EXPLORER_EXECUTABLE} "{directory_path.resolve()}"'


def is_same_windows_path(left_path: Path, right_path: Path) -> bool:
    return normalize_windows_path(left_path) == normalize_windows_path(right_path)


def normalize_windows_path(path: Path) -> str:
    return str(path.resolve()).rstrip("\\/").casefold()
