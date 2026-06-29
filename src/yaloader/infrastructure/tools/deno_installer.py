from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from yaloader.application.dto.tool_installation import (
    ToolId,
    ToolInstallationResult,
    build_tool_installation_progress,
)
from yaloader.application.ports.tool_installer import ToolInstallationProgressCallback
from yaloader.config.paths import AppPaths
from yaloader.infrastructure.tools.archive_extraction import (
    ArchiveExtractionError,
    safe_extract_zip_archive,
)
from yaloader.infrastructure.tools.http_file_downloader import (
    FileDownloader,
    FileDownloadError,
    HttpFileDownloader,
)
from yaloader.infrastructure.tools.version_detection import (
    normalize_tool_version,
    run_executable_for_text,
)

DENO_LATEST_VERSION_URL = "https://dl.deno.land/release-latest.txt"
DENO_WINDOWS_X64_ZIP_URL_TEMPLATE = "https://dl.deno.land/release/{version}/deno-x86_64-pc-windows-msvc.zip"

VERSION_RESOLUTION_PERCENT = 8
DOWNLOAD_START_PERCENT = 10
DOWNLOAD_END_PERCENT = 76
EXTRACTION_PERCENT = 84
INSTALLATION_PERCENT = 92
COMPLETED_PERCENT = 100

TEMPORARY_TOOLS_DIR_NAME = "_tmp"
INSTALLING_DIR_SUFFIX = ".installing"
PREVIOUS_DIR_SUFFIX = ".previous"
DENO_EXECUTABLE_FILE_NAME = "deno.exe"


class DenoPortableInstallationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DenoPortableInstaller:
    paths: AppPaths
    downloader: FileDownloader = field(default_factory=HttpFileDownloader)

    @property
    def tool_id(self) -> ToolId:
        return ToolId.DENO

    def install(
        self,
        progress_callback: ToolInstallationProgressCallback | None = None,
        force_reinstall: bool = False,
    ) -> ToolInstallationResult:
        if self.paths.deno_executable.is_file() and not force_reinstall:
            self._emit_progress(
                progress_callback=progress_callback,
                message="Deno уже установлен в папке YaLoader",
                percent=COMPLETED_PERCENT,
                path=self.paths.deno_executable,
            )
            return ToolInstallationResult.installed(
                tool_id=self.tool_id,
                executable_path=self.paths.deno_executable,
            )

        temporary_root_dir = self._build_temporary_root_dir()

        try:
            self._emit_progress(
                progress_callback=progress_callback,
                message="Готовим установку Deno",
                percent=0,
            )
            remove_directory_if_exists(directory_path=temporary_root_dir)
            temporary_root_dir.mkdir(parents=True, exist_ok=True)

            archive_file = temporary_root_dir / "deno-x86_64-pc-windows-msvc.zip"
            extracted_dir = temporary_root_dir / "extracted"

            version = self._resolve_latest_version(progress_callback=progress_callback)
            self._download_archive(
                version=version,
                archive_file=archive_file,
                progress_callback=progress_callback,
            )
            self._extract_archive(
                archive_file=archive_file,
                extracted_dir=extracted_dir,
                progress_callback=progress_callback,
            )
            source_executable = find_deno_executable(extracted_dir=extracted_dir)
            self._replace_installation(
                source_executable=source_executable,
                temporary_root_dir=temporary_root_dir,
                progress_callback=progress_callback,
            )

            self._emit_progress(
                progress_callback=progress_callback,
                message=f"Deno {version} установлен",
                percent=COMPLETED_PERCENT,
                path=self.paths.deno_executable,
            )
            return ToolInstallationResult.installed(
                tool_id=self.tool_id,
                executable_path=self.paths.deno_executable,
            )
        except (
            OSError,
            ArchiveExtractionError,
            DenoPortableInstallationError,
            FileDownloadError,
        ) as error:
            return ToolInstallationResult.failed(
                tool_id=self.tool_id,
                message=f"Не удалось установить Deno: {error}",
            )
        finally:
            remove_directory_if_exists(directory_path=temporary_root_dir)
            remove_directory_if_empty(directory_path=temporary_root_dir.parent)

    def get_latest_version(self) -> str:
        return normalize_tool_version(
            text=self._resolve_latest_version(progress_callback=None),
            prefix="v",
        )

    def get_installed_version(self, *, executable_path: Path) -> str:
        return normalize_tool_version(
            text=run_executable_for_text(
                executable_path=executable_path,
                args=("--version",),
            ),
            prefix="v",
        )

    def _resolve_latest_version(
        self,
        *,
        progress_callback: ToolInstallationProgressCallback | None,
    ) -> str:
        self._emit_progress(
            progress_callback=progress_callback,
            message="Получаем актуальную версию Deno",
            percent=VERSION_RESOLUTION_PERCENT,
        )
        version_text = self.downloader.download_text(url=DENO_LATEST_VERSION_URL)

        return parse_deno_release_version(text=version_text)

    def _download_archive(
        self,
        *,
        version: str,
        archive_file: Path,
        progress_callback: ToolInstallationProgressCallback | None,
    ) -> None:
        self._emit_progress(
            progress_callback=progress_callback,
            message=f"Скачиваем Deno {version}",
            percent=DOWNLOAD_START_PERCENT,
        )

        self.downloader.download_file(
            url=build_deno_windows_x64_zip_url(version=version),
            destination_file=archive_file,
            progress_callback=lambda downloaded_bytes, total_bytes: self._handle_download_progress(
                downloaded_bytes=downloaded_bytes,
                total_bytes=total_bytes,
                progress_callback=progress_callback,
            ),
        )

        self._emit_progress(
            progress_callback=progress_callback,
            message=f"Deno {version} скачан",
            percent=DOWNLOAD_END_PERCENT,
        )

    def _handle_download_progress(
        self,
        *,
        downloaded_bytes: int,
        total_bytes: int | None,
        progress_callback: ToolInstallationProgressCallback | None,
    ) -> None:
        if total_bytes is None or total_bytes <= 0:
            return

        download_range = DOWNLOAD_END_PERCENT - DOWNLOAD_START_PERCENT
        percent = DOWNLOAD_START_PERCENT + round(downloaded_bytes / total_bytes * download_range)
        bounded_percent = max(DOWNLOAD_START_PERCENT, min(DOWNLOAD_END_PERCENT, percent))

        self._emit_progress(
            progress_callback=progress_callback,
            message="Скачиваем Deno",
            percent=bounded_percent,
        )

    def _extract_archive(
        self,
        *,
        archive_file: Path,
        extracted_dir: Path,
        progress_callback: ToolInstallationProgressCallback | None,
    ) -> None:
        self._emit_progress(
            progress_callback=progress_callback,
            message="Распаковываем Deno",
            percent=EXTRACTION_PERCENT,
        )
        safe_extract_zip_archive(
            archive_file=archive_file,
            destination_dir=extracted_dir,
        )

    def _replace_installation(
        self,
        *,
        source_executable: Path,
        temporary_root_dir: Path,
        progress_callback: ToolInstallationProgressCallback | None,
    ) -> None:
        self._emit_progress(
            progress_callback=progress_callback,
            message="Устанавливаем Deno",
            percent=INSTALLATION_PERCENT,
        )

        staging_dir = temporary_root_dir / f"{self.paths.deno_dir.name}{INSTALLING_DIR_SUFFIX}"
        previous_dir = self.paths.deno_dir.with_name(
            f"{self.paths.deno_dir.name}{PREVIOUS_DIR_SUFFIX}",
        )

        remove_directory_if_exists(directory_path=staging_dir)
        remove_directory_if_exists(directory_path=previous_dir)

        staging_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_executable, staging_dir / DENO_EXECUTABLE_FILE_NAME)

        staging_executable = staging_dir / DENO_EXECUTABLE_FILE_NAME

        if not staging_executable.is_file():
            raise DenoPortableInstallationError(
                f"deno.exe not found after staging: {staging_executable}",
            )

        if self.paths.deno_dir.exists():
            shutil.move(str(self.paths.deno_dir), str(previous_dir))

        try:
            shutil.move(str(staging_dir), str(self.paths.deno_dir))
        except OSError:
            if previous_dir.exists() and not self.paths.deno_dir.exists():
                shutil.move(str(previous_dir), str(self.paths.deno_dir))

            raise

        remove_directory_if_exists(directory_path=previous_dir)

        if not self.paths.deno_executable.is_file():
            raise DenoPortableInstallationError(
                f"deno.exe not found after installation: {self.paths.deno_executable}",
            )

    def _build_temporary_root_dir(self) -> Path:
        return self.paths.tools_dir / TEMPORARY_TOOLS_DIR_NAME / f"deno-{uuid4().hex}"

    def _emit_progress(
        self,
        *,
        progress_callback: ToolInstallationProgressCallback | None,
        message: str,
        percent: int | None = None,
        path: Path | None = None,
    ) -> None:
        if progress_callback is None:
            return

        progress_callback(
            build_tool_installation_progress(
                tool_id=self.tool_id,
                message=message,
                percent=percent,
                path=path,
            )
        )


def parse_deno_release_version(*, text: str) -> str:
    version = text.strip()

    if not version:
        raise DenoPortableInstallationError("latest Deno version response is empty")

    if not version.startswith("v"):
        raise DenoPortableInstallationError(f"invalid Deno release version: {version}")

    version_parts = version.removeprefix("v").split(".")

    if len(version_parts) < 3:
        raise DenoPortableInstallationError(f"invalid Deno release version: {version}")

    if any(not part.isdigit() for part in version_parts[:3]):
        raise DenoPortableInstallationError(f"invalid Deno release version: {version}")

    return version


def build_deno_windows_x64_zip_url(*, version: str) -> str:
    return DENO_WINDOWS_X64_ZIP_URL_TEMPLATE.format(version=version)


def find_deno_executable(*, extracted_dir: Path) -> Path:
    for file_path in extracted_dir.rglob("*"):
        if file_path.is_file() and file_path.name.casefold() == DENO_EXECUTABLE_FILE_NAME:
            return file_path

    raise DenoPortableInstallationError(
        f"deno.exe not found in extracted archive: {extracted_dir}",
    )


def remove_directory_if_exists(*, directory_path: Path) -> None:
    if directory_path.exists():
        shutil.rmtree(directory_path)


def remove_directory_if_empty(*, directory_path: Path) -> None:
    try:
        directory_path.rmdir()
    except OSError:
        return
