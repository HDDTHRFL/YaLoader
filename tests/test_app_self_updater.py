from __future__ import annotations

from pathlib import Path

import pytest

from yaloader.application.dto.app_update import AppReleaseInfo
from yaloader.infrastructure.windows.app_self_updater import (
    AppSelfUpdateError,
    build_updater_command_text,
    escape_batch_value,
    find_yaloader_executable,
    resolve_release_archive_file_name,
    sanitize_update_asset_file_name,
    sanitize_update_version_dir_name,
)


def test_sanitize_update_version_dir_name_keeps_release_version() -> None:
    assert sanitize_update_version_dir_name(version="1.2.3") == "1.2.3"


def test_sanitize_update_version_dir_name_rejects_empty_version() -> None:
    with pytest.raises(AppSelfUpdateError):
        sanitize_update_version_dir_name(version="...")


def test_sanitize_update_asset_file_name_keeps_only_file_name() -> None:
    assert sanitize_update_asset_file_name(file_name="../YaLoader.zip") == "YaLoader.zip"


def test_resolve_release_archive_file_name_uses_github_asset_name() -> None:
    archive_name = resolve_release_archive_file_name(
        release_info=AppReleaseInfo(
            version="1.2.3",
            archive_name="YaLoader-v1.2.3-windows-x64.zip",
        ),
    )

    assert archive_name == "YaLoader-v1.2.3-windows-x64.zip"


def test_resolve_release_archive_file_name_builds_default_name() -> None:
    archive_name = resolve_release_archive_file_name(
        release_info=AppReleaseInfo(version="1.2.3"),
    )

    assert archive_name == "YaLoader-v1.2.3-windows-x64.zip"


def test_find_yaloader_executable_recurses_extracted_archive(tmp_path: Path) -> None:
    executable_file = tmp_path / "YaLoader" / "YaLoader.exe"
    executable_file.parent.mkdir(parents=True)
    executable_file.write_bytes(b"exe")

    assert find_yaloader_executable(extracted_dir=tmp_path) == executable_file


def test_find_yaloader_executable_rejects_missing_executable(tmp_path: Path) -> None:
    with pytest.raises(AppSelfUpdateError):
        find_yaloader_executable(extracted_dir=tmp_path)


def test_escape_batch_value_escapes_percent_sign() -> None:
    assert escape_batch_value(value="C:/Users/%USERNAME%/YaLoader.exe") == ("C:/Users/%%USERNAME%%/YaLoader.exe")


def test_build_updater_command_text_waits_replaces_and_restarts() -> None:
    command_text = build_updater_command_text(
        current_process_id=1234,
        staged_executable=Path("C:/Temp/YaLoader.exe"),
        target_executable=Path("C:/Apps/YaLoader.exe"),
        backup_executable=Path("C:/Apps/YaLoader.exe.previous"),
        log_file=Path("C:/Temp/update.log"),
    )

    assert "PID eq %YALOADER_PID%" in command_text
    assert "copy /Y" in command_text
    assert "YaLoader.exe.previous" in command_text
    assert 'start "" "%YALOADER_TARGET%"' in command_text
