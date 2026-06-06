from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from yaloader.application.dto.tool_installation import (
    ToolInstallationProgress,
    ToolInstallationStatus,
)
from yaloader.config.paths import AppPaths
from yaloader.infrastructure.tools.checksum import calculate_file_sha256
from yaloader.infrastructure.tools.ffmpeg_installer import (
    FfmpegPortableInstaller,
    find_ffmpeg_source_root,
)
from yaloader.infrastructure.tools.http_file_downloader import ArchiveDownloadProgressCallback


@dataclass(frozen=True, slots=True)
class FakeFileDownloader:
    archive_file: Path
    checksum_text: str | None = None

    def download_file(
        self,
        *,
        url: str,
        destination_file: Path,
        progress_callback: ArchiveDownloadProgressCallback | None = None,
    ) -> None:
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.archive_file, destination_file)

        if progress_callback is not None:
            archive_size = destination_file.stat().st_size
            progress_callback(archive_size, archive_size)

    def download_text(self, *, url: str) -> str:
        if self.checksum_text is not None:
            return self.checksum_text

        return calculate_file_sha256(file_path=self.archive_file)


def test_find_ffmpeg_source_root_returns_parent_of_bin_dir(tmp_path: Path) -> None:
    source_root_dir = tmp_path / "extracted" / "ffmpeg-8.1.1-essentials_build"
    executable_file = source_root_dir / "bin" / "ffmpeg.exe"
    executable_file.parent.mkdir(parents=True)
    executable_file.write_text("fake ffmpeg", encoding="utf-8")

    assert find_ffmpeg_source_root(extracted_dir=tmp_path / "extracted") == source_root_dir


def test_ffmpeg_portable_installer_installs_ffmpeg_from_zip(tmp_path: Path) -> None:
    archive_file = create_ffmpeg_archive(tmp_path=tmp_path)
    paths = create_app_paths(tmp_path=tmp_path)
    progress_events: list[ToolInstallationProgress] = []

    installer = FfmpegPortableInstaller(
        paths=paths,
        downloader=FakeFileDownloader(archive_file=archive_file),
    )

    result = installer.install(progress_callback=progress_events.append)

    assert result.status is ToolInstallationStatus.INSTALLED
    assert result.executable_path == paths.ffmpeg_executable
    assert paths.ffmpeg_executable.read_text(encoding="utf-8") == "fake ffmpeg"
    assert paths.ffmpeg_dir.is_dir()
    assert not (paths.tools_dir / "_tmp").exists()
    assert progress_events[-1].percent == 100
    assert progress_events[-1].path == paths.ffmpeg_executable


def test_ffmpeg_portable_installer_returns_installed_when_ffmpeg_already_exists(
    tmp_path: Path,
) -> None:
    archive_file = create_ffmpeg_archive(tmp_path=tmp_path)
    paths = create_app_paths(tmp_path=tmp_path)
    paths.ffmpeg_executable.parent.mkdir(parents=True)
    paths.ffmpeg_executable.write_text("existing ffmpeg", encoding="utf-8")

    installer = FfmpegPortableInstaller(
        paths=paths,
        downloader=FakeFileDownloader(archive_file=archive_file),
    )

    result = installer.install()

    assert result.status is ToolInstallationStatus.INSTALLED
    assert result.executable_path == paths.ffmpeg_executable
    assert paths.ffmpeg_executable.read_text(encoding="utf-8") == "existing ffmpeg"


def test_ffmpeg_portable_installer_rejects_invalid_checksum(tmp_path: Path) -> None:
    archive_file = create_ffmpeg_archive(tmp_path=tmp_path)
    paths = create_app_paths(tmp_path=tmp_path)

    installer = FfmpegPortableInstaller(
        paths=paths,
        downloader=FakeFileDownloader(
            archive_file=archive_file,
            checksum_text="0" * 64,
        ),
    )

    result = installer.install()

    assert result.status is ToolInstallationStatus.FAILED
    assert result.executable_path is None
    assert "SHA-256" not in result.message
    assert not paths.ffmpeg_executable.exists()


def test_ffmpeg_portable_installer_rejects_archive_without_ffmpeg(tmp_path: Path) -> None:
    archive_file = tmp_path / "ffmpeg.zip"

    with ZipFile(archive_file, mode="w") as archive:
        archive.writestr("readme.txt", "no executable")

    paths = create_app_paths(tmp_path=tmp_path)
    installer = FfmpegPortableInstaller(
        paths=paths,
        downloader=FakeFileDownloader(archive_file=archive_file),
    )

    result = installer.install()

    assert result.status is ToolInstallationStatus.FAILED
    assert "ffmpeg.exe not found" in result.message
    assert not paths.ffmpeg_executable.exists()


def create_ffmpeg_archive(*, tmp_path: Path) -> Path:
    archive_file = tmp_path / "ffmpeg.zip"

    with ZipFile(archive_file, mode="w") as archive:
        archive.writestr(
            "ffmpeg-8.1.1-essentials_build/bin/ffmpeg.exe",
            "fake ffmpeg",
        )
        archive.writestr(
            "ffmpeg-8.1.1-essentials_build/bin/ffprobe.exe",
            "fake ffprobe",
        )

    return archive_file


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
