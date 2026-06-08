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
from yaloader.infrastructure.tools.deno_installer import (
    DenoPortableInstaller,
    build_deno_windows_x64_zip_url,
    find_deno_executable,
    parse_deno_release_version,
)
from yaloader.infrastructure.tools.http_file_downloader import ArchiveDownloadProgressCallback


@dataclass(frozen=True, slots=True)
class FakeFileDownloader:
    archive_file: Path
    version_text: str = "v2.8.2"

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
        return self.version_text


def test_parse_deno_release_version_accepts_version() -> None:
    assert parse_deno_release_version(text="v2.8.2\n") == "v2.8.2"


def test_parse_deno_release_version_rejects_invalid_version() -> None:
    try:
        parse_deno_release_version(text="latest\n")
    except Exception as error:
        assert "invalid Deno release version" in str(error)
    else:
        raise AssertionError("DenoPortableInstallationError was not raised")


def test_build_deno_windows_x64_zip_url_uses_release_version() -> None:
    assert build_deno_windows_x64_zip_url(version="v2.8.2") == (
        "https://dl.deno.land/release/v2.8.2/deno-x86_64-pc-windows-msvc.zip"
    )


def test_find_deno_executable_returns_executable_path(tmp_path: Path) -> None:
    executable_file = tmp_path / "extracted" / "deno.exe"
    executable_file.parent.mkdir(parents=True)
    executable_file.write_text("fake deno", encoding="utf-8")

    assert find_deno_executable(extracted_dir=tmp_path / "extracted") == executable_file


def test_deno_portable_installer_installs_deno_from_zip(tmp_path: Path) -> None:
    archive_file = create_deno_archive(tmp_path=tmp_path)
    paths = create_app_paths(tmp_path=tmp_path)
    progress_events: list[ToolInstallationProgress] = []

    installer = DenoPortableInstaller(
        paths=paths,
        downloader=FakeFileDownloader(archive_file=archive_file),
    )

    result = installer.install(progress_callback=progress_events.append)

    assert result.status is ToolInstallationStatus.INSTALLED
    assert result.executable_path == paths.deno_executable
    assert paths.deno_executable.read_text(encoding="utf-8") == "fake deno"
    assert paths.deno_dir.is_dir()
    assert not (paths.tools_dir / "_tmp").exists()
    assert progress_events[-1].percent == 100
    assert progress_events[-1].path == paths.deno_executable


def test_deno_portable_installer_returns_installed_when_deno_already_exists(
    tmp_path: Path,
) -> None:
    archive_file = create_deno_archive(tmp_path=tmp_path)
    paths = create_app_paths(tmp_path=tmp_path)
    paths.deno_executable.parent.mkdir(parents=True)
    paths.deno_executable.write_text("existing deno", encoding="utf-8")

    installer = DenoPortableInstaller(
        paths=paths,
        downloader=FakeFileDownloader(archive_file=archive_file),
    )

    result = installer.install()

    assert result.status is ToolInstallationStatus.INSTALLED
    assert result.executable_path == paths.deno_executable
    assert paths.deno_executable.read_text(encoding="utf-8") == "existing deno"


def test_deno_portable_installer_force_reinstall_replaces_existing_deno(
    tmp_path: Path,
) -> None:
    archive_file = create_deno_archive(tmp_path=tmp_path)
    paths = create_app_paths(tmp_path=tmp_path)
    paths.deno_executable.parent.mkdir(parents=True)
    paths.deno_executable.write_text("existing deno", encoding="utf-8")

    installer = DenoPortableInstaller(
        paths=paths,
        downloader=FakeFileDownloader(archive_file=archive_file),
    )

    result = installer.install(force_reinstall=True)

    assert result.status is ToolInstallationStatus.INSTALLED
    assert result.executable_path == paths.deno_executable
    assert paths.deno_executable.read_text(encoding="utf-8") == "fake deno"


def test_deno_portable_installer_rejects_invalid_latest_version(tmp_path: Path) -> None:
    archive_file = create_deno_archive(tmp_path=tmp_path)
    paths = create_app_paths(tmp_path=tmp_path)

    installer = DenoPortableInstaller(
        paths=paths,
        downloader=FakeFileDownloader(
            archive_file=archive_file,
            version_text="invalid-version",
        ),
    )

    result = installer.install()

    assert result.status is ToolInstallationStatus.FAILED
    assert "invalid Deno release version" in result.message
    assert not paths.deno_executable.exists()


def test_deno_portable_installer_rejects_archive_without_deno(tmp_path: Path) -> None:
    archive_file = tmp_path / "deno.zip"

    with ZipFile(archive_file, mode="w") as archive:
        archive.writestr("readme.txt", "no executable")

    paths = create_app_paths(tmp_path=tmp_path)
    installer = DenoPortableInstaller(
        paths=paths,
        downloader=FakeFileDownloader(archive_file=archive_file),
    )

    result = installer.install()

    assert result.status is ToolInstallationStatus.FAILED
    assert "deno.exe not found" in result.message
    assert not paths.deno_executable.exists()


def create_deno_archive(*, tmp_path: Path) -> Path:
    archive_file = tmp_path / "deno.zip"

    with ZipFile(archive_file, mode="w") as archive:
        archive.writestr("deno.exe", "fake deno")

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
