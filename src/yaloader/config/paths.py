from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from yaloader.config.app_info import APP_NAME


@dataclass(frozen=True, slots=True)
class AppPaths:
    data_dir: Path
    downloads_dir: Path
    logs_dir: Path
    settings_file: Path

    @property
    def required_directories(self) -> tuple[Path, ...]:
        return (
            self.data_dir,
            self.downloads_dir,
            self.logs_dir,
        )


def build_default_app_paths() -> AppPaths:
    data_dir = get_default_data_dir()
    downloads_dir = Path.home() / "Downloads" / "YaLoader"

    return AppPaths(
        data_dir=data_dir,
        downloads_dir=downloads_dir,
        logs_dir=data_dir / "logs",
        settings_file=data_dir / "settings.json",
    )


def get_default_data_dir() -> Path:
    appdata_dir = os.getenv("APPDATA")

    if appdata_dir is not None:
        return Path(appdata_dir) / APP_NAME

    return Path.home() / ".config" / APP_NAME


def ensure_app_directories(paths: AppPaths) -> None:
    for directory in paths.required_directories:
        directory.mkdir(parents=True, exist_ok=True)
