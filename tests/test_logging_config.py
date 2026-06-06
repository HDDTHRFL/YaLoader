from __future__ import annotations

import sys
from pathlib import Path

from pytest import MonkeyPatch

from yaloader.config.logging_config import LOG_FILE_NAME, configure_application_logging
from yaloader.config.paths import AppPaths


def test_configure_application_logging_creates_logs_directory(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)

    log_file_path = configure_application_logging(paths=paths)

    assert log_file_path == paths.logs_dir / LOG_FILE_NAME
    assert paths.logs_dir.is_dir()


def test_configure_application_logging_works_without_stderr(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    paths = create_app_paths(tmp_path=tmp_path)
    monkeypatch.setattr(sys, "stderr", None)

    log_file_path = configure_application_logging(paths=paths)

    assert log_file_path == paths.logs_dir / LOG_FILE_NAME
    assert log_file_path.is_file()


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
