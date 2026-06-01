from __future__ import annotations

from pathlib import Path

from yaloader.application.dto.app_settings import AppSettings
from yaloader.application.services.settings_service import SettingsService


def test_load_returns_default_settings_when_file_does_not_exist(tmp_path: Path) -> None:
    default_downloads_dir = tmp_path / "downloads"
    service = SettingsService(
        settings_file=tmp_path / "settings.json",
        default_downloads_dir=default_downloads_dir,
    )

    settings = service.load()

    assert settings.downloads_dir == default_downloads_dir


def test_save_and_load_settings(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    downloads_dir = tmp_path / "custom-downloads"
    service = SettingsService(
        settings_file=settings_file,
        default_downloads_dir=tmp_path / "downloads",
    )

    service.save(AppSettings(downloads_dir=downloads_dir))

    loaded_settings = service.load()

    assert loaded_settings.downloads_dir == downloads_dir


def test_update_downloads_dir_saves_settings(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    downloads_dir = tmp_path / "selected-downloads"
    service = SettingsService(
        settings_file=settings_file,
        default_downloads_dir=tmp_path / "downloads",
    )

    settings = service.update_downloads_dir(downloads_dir=downloads_dir)

    assert settings.downloads_dir == downloads_dir
    assert service.load().downloads_dir == downloads_dir


def test_load_returns_default_settings_when_file_is_invalid(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    default_downloads_dir = tmp_path / "downloads"
    settings_file.write_text("{invalid json", encoding="utf-8")

    service = SettingsService(
        settings_file=settings_file,
        default_downloads_dir=default_downloads_dir,
    )

    settings = service.load()

    assert settings.downloads_dir == default_downloads_dir


def test_update_download_speed_limit_saves_settings(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    service = SettingsService(
        settings_file=settings_file,
        default_downloads_dir=tmp_path / "downloads",
    )

    settings = service.update_download_speed_limit(bytes_per_second=1_048_576)

    assert settings.download_speed_limit_bytes_per_second == 1_048_576
    assert service.load().download_speed_limit_bytes_per_second == 1_048_576


def test_update_downloads_dir_preserves_download_speed_limit(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    first_downloads_dir = tmp_path / "downloads"
    second_downloads_dir = tmp_path / "selected-downloads"
    service = SettingsService(
        settings_file=settings_file,
        default_downloads_dir=first_downloads_dir,
    )

    service.update_download_speed_limit(bytes_per_second=1_048_576)
    settings = service.update_downloads_dir(downloads_dir=second_downloads_dir)

    assert settings.downloads_dir == second_downloads_dir
    assert settings.download_speed_limit_bytes_per_second == 1_048_576
