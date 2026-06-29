from __future__ import annotations

from pathlib import Path

import pytest

from yaloader.infrastructure.windows.app_self_updater import (
    AppSelfUpdateError,
    build_updater_command_text,
    escape_batch_value,
    sanitize_update_version_dir_name,
)


def test_sanitize_update_version_dir_name_keeps_release_version() -> None:
    assert sanitize_update_version_dir_name(version="1.2.3") == "1.2.3"


def test_sanitize_update_version_dir_name_rejects_empty_version() -> None:
    with pytest.raises(AppSelfUpdateError):
        sanitize_update_version_dir_name(version="...")


def test_escape_batch_value_escapes_percent_sign() -> None:
    assert escape_batch_value(value="C:/Users/%USERNAME%/YaLoader.exe") == (
        "C:/Users/%%USERNAME%%/YaLoader.exe"
    )


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
