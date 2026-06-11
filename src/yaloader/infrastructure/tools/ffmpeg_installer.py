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
from yaloader.infrastructure.tools.version_detection import (
    normalize_tool_version,
    run_executable_for_text,
)

FFMPEG_RELEASE_ESSENTIALS_ZIP_URL = (
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
)
FFMPEG_RELEASE_ESSENTIALS_SHA256_URL = (
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.sha256"
)
FFMPEG_RELEASE_VERSION_URL = "https://www.gyan.dev/ffmpeg/builds/release-version"

DOWNLOAD_START_PERCENT = 10
DOWNLOAD_END_PERCENT = 70
CHECKSUM_PERCENT = 72
EXTRACTION_PERCENT = 82
INSTALLATION_PERCENT = 92
COMPLETED_PERCENT = 100

TEMPORARY_TOOLS_DIR_NAME = "_tmp"
INSTALLING_DIR_SUFFIX = ".installing"
PREVIOUS_DIR_SUFFIX = ".previous"


class FfmpegPortableInstallationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FfmpegPortableInstaller:
    paths: AppPaths
    downloader: FileDownloader = field(default_factory=HttpFileDownloader)

    @property
    def tool_id(self) -> ToolId:
        return ToolId.FFMPEG

    def get_latest_version(self) -> str:
        return normalize_tool_version(
            text=self.downloader.download_text(url=FFMPEG_RELEASE_VERSION_URL),
        )

    def get_installed_version(self, *, executable_path: Path) -> str:
        return normalize_tool_version(
            text=run_executable_for_text(
                executable_path=executable_path,
                args=("-version",),
            ),
        )

    def install(
        self,
        progress_callback: ToolInstallationProgressCallback | None = None,
        force_reinstall: bool = False,
    ) -> ToolInstallationResult:
        if self.paths.ffmpeg_executable.is_file() and not force_reinstall:
            self._emit_progress(
                progress_callback=progress_callback,
                message="FFmpeg уже установлен в папке YaLoader",
                percent=COMPLETED_PERCENT,
                path=self.paths.ffmpeg_executable,
            )
            return ToolInstallationResult.installed(
                tool_id=self.tool_id,
                executable_path=self.paths.ffmpeg_executable,
            )

        temporary_root_dir = self._build_temporary_root_dir()

        try:
            self._emit_progress(
                progress_callback=progress_callback,
                message="Готовим установку FFmpeg",
                percent=0,
            )
            remove_directory_if_exists(directory_path=temporary_root_dir)
            temporary_root_dir.mkdir(parents=True, exist_ok=True)

            archive_file = temporary_root_dir / "ffmpeg-release-essentials.zip"
            extracted_dir = temporary_root_dir / "extracted"

            self._download_archive(
                archive_file=archive_file,
                progress_callback=progress_callback,
            )
            self._verify_archive(
                archive_file=archive_file,
                progress_callback=progress_callback,
            )
            self._extract_archive(
                archive_file=archive_file,
                extracted_dir=extracted_dir,
                progress_callback=progress_callback,
            )
            source_root_dir = find_ffmpeg_source_root(extracted_dir=extracted_dir)
            self._replace_installation(
                source_root_dir=source_root_dir,
                temporary_root_dir=temporary_root_dir,
                progress_callback=progress_callback,
            )

            self._emit_progress(
                progress_callback=progress_callback,
                message="FFmpeg установлен",
                percent=COMPLETED_PERCENT,
                path=self.paths.ffmpeg_executable,
            )
            return ToolInstallationResult.installed(
                tool_id=self.tool_id,
                executable_path=self.paths.ffmpeg_executable,
            )
        except (
            OSError,
            ArchiveExtractionError,
            ChecksumError,
            FfmpegPortableInstallationError,
            FileDownloadError,
        ) as error:
            return ToolInstallationResult.failed(
                tool_id=self.tool_id,
                message=f"Не удалось установить FFmpeg: {error}",
            )
        finally:
            remove_directory_if_exists(directory_path=temporary_root_dir)
            remove_directory_if_empty(directory_path=temporary_root_dir.parent)

    def _download_archive(
        self,
        *,
        archive_file: Path,
        progress_callback: ToolInstallationProgressCallback | None,
    ) -> None:
        self._emit_progress(
            progress_callback=progress_callback,
            message="Скачиваем FFmpeg",
            percent=DOWNLOAD_START_PERCENT,
        )

        self.downloader.download_file(
            url=FFMPEG_RELEASE_ESSENTIALS_ZIP_URL,
            destination_file=archive_file,
            progress_callback=lambda downloaded_bytes, total_bytes: self._handle_download_progress(
                downloaded_bytes=downloaded_bytes,
                total_bytes=total_bytes,
                progress_callback=progress_callback,
            ),
        )

        self._emit_progress(
            progress_callback=progress_callback,
            message="FFmpeg скачан",
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
            message="Скачиваем FFmpeg",
            percent=bounded_percent,
        )

    def _verify_archive(
        self,
        *,
        archive_file: Path,
        progress_callback: ToolInstallationProgressCallback | None,
    ) -> None:
        self._emit_progress(
            progress_callback=progress_callback,
            message="Проверяем SHA-256 FFmpeg",
            percent=CHECKSUM_PERCENT,
        )
        checksum_text = self.downloader.download_text(url=FFMPEG_RELEASE_ESSENTIALS_SHA256_URL)
        expected_sha256 = parse_sha256_text(text=checksum_text)
        verify_file_sha256(
            file_path=archive_file,
            expected_sha256=expected_sha256,
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
            message="Распаковываем FFmpeg",
            percent=EXTRACTION_PERCENT,
        )
        safe_extract_zip_archive(
            archive_file=archive_file,
            destination_dir=extracted_dir,
        )

    def _replace_installation(
        self,
        *,
        source_root_dir: Path,
        temporary_root_dir: Path,
        progress_callback: ToolInstallationProgressCallback | None,
    ) -> None:
        self._emit_progress(
            progress_callback=progress_callback,
            message="Устанавливаем FFmpeg",
            percent=INSTALLATION_PERCENT,
        )

        staging_dir = temporary_root_dir / f"{self.paths.ffmpeg_dir.name}{INSTALLING_DIR_SUFFIX}"
        previous_dir = self.paths.ffmpeg_dir.with_name(
            f"{self.paths.ffmpeg_dir.name}{PREVIOUS_DIR_SUFFIX}",
        )

        remove_directory_if_exists(directory_path=staging_dir)
        remove_directory_if_exists(directory_path=previous_dir)

        shutil.copytree(source_root_dir, staging_dir)

        staging_executable = staging_dir / "bin" / "ffmpeg.exe"

        if not staging_executable.is_file():
            raise FfmpegPortableInstallationError(
                f"ffmpeg.exe not found after staging: {staging_executable}",
            )

        if self.paths.ffmpeg_dir.exists():
            shutil.move(str(self.paths.ffmpeg_dir), str(previous_dir))

        try:
            shutil.move(str(staging_dir), str(self.paths.ffmpeg_dir))
        except OSError:
            if previous_dir.exists() and not self.paths.ffmpeg_dir.exists():
                shutil.move(str(previous_dir), str(self.paths.ffmpeg_dir))

            raise

        remove_directory_if_exists(directory_path=previous_dir)

        if not self.paths.ffmpeg_executable.is_file():
            raise FfmpegPortableInstallationError(
                f"ffmpeg.exe not found after installation: {self.paths.ffmpeg_executable}",
            )

    def _build_temporary_root_dir(self) -> Path:
        return self.paths.tools_dir / TEMPORARY_TOOLS_DIR_NAME / f"ffmpeg-{uuid4().hex}"

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


def find_ffmpeg_source_root(*, extracted_dir: Path) -> Path:
    for file_path in extracted_dir.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.name.casefold() != "ffmpeg.exe":
            continue

        if file_path.parent.name.casefold() == "bin":
            return file_path.parent.parent

        return file_path.parent

    raise FfmpegPortableInstallationError(
        f"ffmpeg.exe not found in extracted archive: {extracted_dir}",
    )


def remove_directory_if_exists(*, directory_path: Path) -> None:
    if directory_path.exists():
        shutil.rmtree(directory_path)


def remove_directory_if_empty(*, directory_path: Path) -> None:
    try:
        directory_path.rmdir()
    except OSError:
        return
