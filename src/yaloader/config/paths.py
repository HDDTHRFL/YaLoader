from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from yaloader.config.app_info import APP_NAME

TOOLS_DIR_NAME: Final = "tools"
YTDLP_RUNTIME_ROOT_DIR_NAME: Final = "yt-dlp-runtimes"

FFMPEG_DIR_NAME: Final = "ffmpeg"
FFMPEG_BIN_DIR_NAME: Final = "bin"
FFMPEG_EXECUTABLE_NAME: Final = "ffmpeg.exe"

DENO_DIR_NAME: Final = "deno"
DENO_EXECUTABLE_NAME: Final = "deno.exe"

PLATFORM_ICONS_CACHE_DIR_NAME: Final = "platform-icons"


@dataclass(frozen=True, slots=True)
class AppPaths:
    data_dir: Path
    downloads_dir: Path
    logs_dir: Path
    settings_file: Path
    cookies_file: Path
    history_file: Path

    @property
    def tools_dir(self) -> Path:
        return self.data_dir / TOOLS_DIR_NAME

    @property
    def ytdlp_runtime_root_dir(self) -> Path:
        return self.tools_dir / YTDLP_RUNTIME_ROOT_DIR_NAME

    @property
    def platform_icons_cache_dir(self) -> Path:
        return self.data_dir / PLATFORM_ICONS_CACHE_DIR_NAME

    @property
    def ffmpeg_dir(self) -> Path:
        return self.tools_dir / FFMPEG_DIR_NAME

    @property
    def ffmpeg_bin_dir(self) -> Path:
        return self.ffmpeg_dir / FFMPEG_BIN_DIR_NAME

    @property
    def ffmpeg_executable(self) -> Path:
        return self.ffmpeg_bin_dir / FFMPEG_EXECUTABLE_NAME

    @property
    def deno_dir(self) -> Path:
        return self.tools_dir / DENO_DIR_NAME

    @property
    def deno_executable(self) -> Path:
        return self.deno_dir / DENO_EXECUTABLE_NAME

    @property
    def required_directories(self) -> tuple[Path, ...]:
        return (
            self.data_dir,
            self.downloads_dir,
            self.logs_dir,
            self.tools_dir,
            self.ytdlp_runtime_root_dir,
            self.platform_icons_cache_dir,
        )


def build_default_app_paths() -> AppPaths:
    data_dir = get_default_data_dir()
    downloads_dir = Path.home() / "Downloads" / "YaLoader"

    return AppPaths(
        data_dir=data_dir,
        downloads_dir=downloads_dir,
        logs_dir=data_dir / "logs",
        settings_file=data_dir / "settings.json",
        cookies_file=data_dir / "cookies.txt",
        history_file=data_dir / "download_history.json",
    )


def get_default_data_dir() -> Path:
    appdata_dir = os.getenv("APPDATA")

    if appdata_dir is not None:
        return Path(appdata_dir) / APP_NAME

    return Path.home() / ".config" / APP_NAME


def ensure_app_directories(paths: AppPaths) -> None:
    for directory in paths.required_directories:
        directory.mkdir(parents=True, exist_ok=True)
