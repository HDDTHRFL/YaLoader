from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from yaloader.application.dto.app_update import (
    YALOADER_EXE_FILE_NAME,
    AppReleaseInfo,
    AppUpdateInstallResult,
    build_yaloader_windows_x64_archive_name,
)
from yaloader.config.paths import AppPaths
from yaloader.infrastructure.tools.archive_extraction import (
    ArchiveExtractionError,
    safe_extract_zip_archive,
)
from yaloader.infrastructure.tools.checksum import ChecksumError, verify_file_sha256
from yaloader.infrastructure.tools.http_file_downloader import (
    FileDownloader,
    FileDownloadError,
    HttpFileDownloader,
)

UPDATES_DIR_NAME: Final = "updates"
UPDATER_COMMAND_FILE_NAME: Final = "apply_yaloader_update.cmd"
UPDATER_LOG_FILE_NAME: Final = "update.log"
EXTRACTED_DIR_NAME: Final = "extracted"
PREVIOUS_EXE_SUFFIX: Final = ".previous"
PYINSTALLER_RESET_ENVIRONMENT_NAME: Final = "PYINSTALLER_RESET_ENVIRONMENT"
PYINSTALLER_RESET_ENVIRONMENT_VALUE: Final = "1"
UPDATED_APP_START_DELAY_SECONDS: Final = 2


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
            ArchiveExtractionError,
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

        if release_info.archive_url is None:
            expected_archive_name = build_yaloader_windows_x64_archive_name(
                version=release_info.version,
            )
            raise AppSelfUpdateError(f"в GitHub release не найден asset {expected_archive_name}")

        if release_info.archive_sha256 is None:
            raise AppSelfUpdateError("GitHub release asset не содержит SHA-256 digest")

        current_executable = get_current_executable_path()
        update_dir = self._prepare_update_dir(version=release_info.version)
        archive_file = update_dir / resolve_release_archive_file_name(release_info=release_info)
        extracted_dir = update_dir / EXTRACTED_DIR_NAME
        staged_executable = update_dir / YALOADER_EXE_FILE_NAME
        command_file = update_dir / UPDATER_COMMAND_FILE_NAME
        log_file = update_dir / UPDATER_LOG_FILE_NAME

        self.downloader.download_file(
            url=release_info.archive_url,
            destination_file=archive_file,
        )
        verify_file_sha256(
            file_path=archive_file,
            expected_sha256=release_info.archive_sha256,
        )
        safe_extract_zip_archive(
            archive_file=archive_file,
            destination_dir=extracted_dir,
        )

        source_executable = find_yaloader_executable(extracted_dir=extracted_dir)
        shutil.copy2(source_executable, staged_executable)

        if not staged_executable.is_file():
            raise AppSelfUpdateError(f"YaLoader.exe не подготовлен: {staged_executable}")

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


def resolve_release_archive_file_name(*, release_info: AppReleaseInfo) -> str:
    archive_name = release_info.archive_name

    if archive_name is None:
        archive_name = build_yaloader_windows_x64_archive_name(version=release_info.version)

    return sanitize_update_asset_file_name(file_name=archive_name)


def sanitize_update_asset_file_name(*, file_name: str) -> str:
    normalized_file_name = Path(file_name.strip()).name

    if not normalized_file_name:
        raise AppSelfUpdateError("имя asset-файла обновления пустое")

    return normalized_file_name


def sanitize_update_version_dir_name(*, version: str) -> str:
    safe_characters = tuple(
        character if character.isalnum() or character in {".", "-", "_"} else "_" for character in version.strip()
    )
    safe_version = "".join(safe_characters).strip("._-")

    if safe_version:
        return safe_version

    raise AppSelfUpdateError("версия обновления пуста")


def find_yaloader_executable(*, extracted_dir: Path) -> Path:
    for file_path in extracted_dir.rglob("*"):
        if file_path.is_file() and file_path.name.casefold() == YALOADER_EXE_FILE_NAME.casefold():
            return file_path

    raise AppSelfUpdateError(f"YaLoader.exe не найден в архиве обновления: {extracted_dir}")


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
            f'set "YALOADER_TARGET_DIR={escape_batch_value(value=str(target_executable.parent))}"',
            f'set "YALOADER_BACKUP={escape_batch_value(value=str(backup_executable))}"',
            f'set "YALOADER_LOG={escape_batch_value(value=str(log_file))}"',
            'echo YaLoader update started. > "%YALOADER_LOG%"',
            'echo Waiting for YaLoader process %YALOADER_PID%... >> "%YALOADER_LOG%"',
            ":wait_for_yaloader_exit",
            ('tasklist /FI "PID eq %YALOADER_PID%" 2>NUL | findstr /C:" %YALOADER_PID% " >NUL'),
            "if not errorlevel 1 (",
            "    timeout /t 1 /nobreak >NUL",
            "    goto wait_for_yaloader_exit",
            ")",
            ('if exist "%YALOADER_BACKUP%" del /f /q "%YALOADER_BACKUP%" >> "%YALOADER_LOG%" 2>&1'),
            ('if exist "%YALOADER_TARGET%" move /Y "%YALOADER_TARGET%" "%YALOADER_BACKUP%" >> "%YALOADER_LOG%" 2>&1'),
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
            ('if exist "%YALOADER_BACKUP%" del /f /q "%YALOADER_BACKUP%" >> "%YALOADER_LOG%" 2>&1'),
            'echo Starting updated YaLoader. >> "%YALOADER_LOG%"',
            f"timeout /t {UPDATED_APP_START_DELAY_SECONDS} /nobreak >NUL",
            f'set "{PYINSTALLER_RESET_ENVIRONMENT_NAME}={PYINSTALLER_RESET_ENVIRONMENT_VALUE}"',
            'start "" /D "%YALOADER_TARGET_DIR%" "%YALOADER_TARGET%"',
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
