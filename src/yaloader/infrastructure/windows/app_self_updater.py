from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from yaloader.application.dto.app_update import (
    YALOADER_EXE_ASSET_NAME,
    YALOADER_EXE_SHA256_ASSET_NAME,
    AppReleaseInfo,
    AppUpdateInstallResult,
)
from yaloader.config.paths import AppPaths
from yaloader.infrastructure.tools.checksum import (
    ChecksumError,
    parse_sha256_text,
    verify_file_sha256,
)
from yaloader.infrastructure.tools.http_file_downloader import (
    FileDownloader,
    FileDownloadError,
    HttpFileDownloader,
)

UPDATES_DIR_NAME: Final = "updates"
UPDATER_COMMAND_FILE_NAME: Final = "apply_yaloader_update.cmd"
UPDATER_LOG_FILE_NAME: Final = "update.log"
PREVIOUS_EXE_SUFFIX: Final = ".previous"


class AppSelfUpdateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class WindowsAppSelfUpdater:
    paths: AppPaths
    downloader: FileDownloader = field(default_factory=HttpFileDownloader)

    def install(self, *, release_info: AppReleaseInfo) -> AppUpdateInstallResult:
        try:
            self._install(release_info=release_info)
        except (
            AppSelfUpdateError,
            ChecksumError,
            FileDownloadError,
            OSError,
            subprocess.SubprocessError,
        ) as error:
            return AppUpdateInstallResult.failed(
                message=f"Не удалось подготовить обновление YaLoader: {error}",
            )

        return AppUpdateInstallResult.ready_to_restart(
            installed_version=release_info.version,
        )

    def _install(self, *, release_info: AppReleaseInfo) -> None:
        if not is_running_from_frozen_executable():
            raise AppSelfUpdateError("автообновление доступно только для собранного YaLoader.exe")

        if release_info.executable_url is None:
            raise AppSelfUpdateError(f"в GitHub release не найден asset {YALOADER_EXE_ASSET_NAME}")

        if release_info.checksum_url is None:
            raise AppSelfUpdateError(
                f"в GitHub release не найден asset {YALOADER_EXE_SHA256_ASSET_NAME}"
            )

        current_executable = get_current_executable_path()
        update_dir = self._prepare_update_dir(version=release_info.version)
        staged_executable = update_dir / YALOADER_EXE_ASSET_NAME
        checksum_file = update_dir / YALOADER_EXE_SHA256_ASSET_NAME
        command_file = update_dir / UPDATER_COMMAND_FILE_NAME
        log_file = update_dir / UPDATER_LOG_FILE_NAME

        self.downloader.download_file(
            url=release_info.executable_url,
            destination_file=staged_executable,
        )
        self.downloader.download_file(
            url=release_info.checksum_url,
            destination_file=checksum_file,
        )

        expected_sha256 = parse_sha256_text(
            text=checksum_file.read_text(encoding="utf-8", errors="replace"),
        )
        verify_file_sha256(
            file_path=staged_executable,
            expected_sha256=expected_sha256,
        )

        write_updater_command_file(
            command_file=command_file,
            current_process_id=os.getpid(),
            staged_executable=staged_executable,
            target_executable=current_executable,
            log_file=log_file,
        )
        launch_updater_command(command_file=command_file)

    def _prepare_update_dir(self, *, version: str) -> Path:
        update_dir = (
            self.paths.data_dir
            / UPDATES_DIR_NAME
            / sanitize_update_version_dir_name(
                version=version,
            )
        )
        remove_directory_if_exists(directory_path=update_dir)
        update_dir.mkdir(parents=True, exist_ok=True)

        return update_dir


def is_running_from_frozen_executable() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_current_executable_path() -> Path:
    return Path(sys.executable).resolve()


def sanitize_update_version_dir_name(*, version: str) -> str:
    safe_characters = tuple(
        character if character.isalnum() or character in {".", "-", "_"} else "_"
        for character in version.strip()
    )
    safe_version = "".join(safe_characters).strip("._-")

    if safe_version:
        return safe_version

    raise AppSelfUpdateError("версия обновления пуста")


def write_updater_command_file(
    *,
    command_file: Path,
    current_process_id: int,
    staged_executable: Path,
    target_executable: Path,
    log_file: Path,
) -> None:
    command_text = build_updater_command_text(
        current_process_id=current_process_id,
        staged_executable=staged_executable,
        target_executable=target_executable,
        backup_executable=target_executable.with_name(
            f"{target_executable.name}{PREVIOUS_EXE_SUFFIX}",
        ),
        log_file=log_file,
    )
    command_file.write_text(command_text, encoding="utf-8", newline="\r\n")


def build_updater_command_text(
    *,
    current_process_id: int,
    staged_executable: Path,
    target_executable: Path,
    backup_executable: Path,
    log_file: Path,
) -> str:
    return "\n".join(
        (
            "@echo off",
            "chcp 65001 >nul",
            "setlocal",
            f'set "YALOADER_PID={current_process_id}"',
            f'set "YALOADER_SOURCE={escape_batch_value(value=str(staged_executable))}"',
            f'set "YALOADER_TARGET={escape_batch_value(value=str(target_executable))}"',
            f'set "YALOADER_BACKUP={escape_batch_value(value=str(backup_executable))}"',
            f'set "YALOADER_LOG={escape_batch_value(value=str(log_file))}"',
            'echo YaLoader update started. > "%YALOADER_LOG%"',
            'echo Waiting for YaLoader process %YALOADER_PID%... >> "%YALOADER_LOG%"',
            ":wait_for_yaloader_exit",
            'tasklist /FI "PID eq %YALOADER_PID%" 2>NUL | findstr /C:" %YALOADER_PID% " >NUL',
            "if not errorlevel 1 (",
            "    timeout /t 1 /nobreak >NUL",
            "    goto wait_for_yaloader_exit",
            ")",
            'if exist "%YALOADER_BACKUP%" del /f /q "%YALOADER_BACKUP%" >> "%YALOADER_LOG%" 2>&1',
            (
                'if exist "%YALOADER_TARGET%" '
                'move /Y "%YALOADER_TARGET%" "%YALOADER_BACKUP%" '
                '>> "%YALOADER_LOG%" 2>&1'
            ),
            'copy /Y "%YALOADER_SOURCE%" "%YALOADER_TARGET%" >> "%YALOADER_LOG%" 2>&1',
            "if errorlevel 1 (",
            '    echo Failed to replace YaLoader executable. >> "%YALOADER_LOG%"',
            (
                '    if exist "%YALOADER_BACKUP%" '
                'move /Y "%YALOADER_BACKUP%" "%YALOADER_TARGET%" '
                '>> "%YALOADER_LOG%" 2>&1'
            ),
            "    exit /b 1",
            ")",
            'if exist "%YALOADER_BACKUP%" del /f /q "%YALOADER_BACKUP%" >> "%YALOADER_LOG%" 2>&1',
            'echo Starting updated YaLoader. >> "%YALOADER_LOG%"',
            'start "" "%YALOADER_TARGET%"',
            "exit /b 0",
            "",
        )
    )


def escape_batch_value(*, value: str) -> str:
    return value.replace("%", "%%")


def launch_updater_command(*, command_file: Path) -> None:
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    subprocess.Popen(
        ("cmd.exe", "/c", str(command_file)),
        cwd=command_file.parent,
        close_fds=True,
        creationflags=creation_flags,
    )


def remove_directory_if_exists(*, directory_path: Path) -> None:
    if directory_path.exists():
        shutil.rmtree(directory_path)
