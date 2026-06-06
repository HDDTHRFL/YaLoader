from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from loguru import logger

from yaloader.application.dto.environment_status import EnvironmentItemStatus, EnvironmentStatus
from yaloader.application.ports.process_runner import ProcessRunner
from yaloader.application.services.cookies_file_service import COOKIES_HEADER_PREFIXES
from yaloader.config.paths import AppPaths


@dataclass(frozen=True, slots=True)
class EnvironmentCheckService:
    paths: AppPaths
    process_runner: ProcessRunner

    def check(self, *, downloads_dir: Path) -> EnvironmentStatus:
        status = EnvironmentStatus(
            ffmpeg=self._check_executable(
                title="FFmpeg",
                executable_name="ffmpeg",
                missing_message="не найден",
            ),
            deno=self._check_executable(
                title="Deno",
                executable_name="deno",
                missing_message="не найден",
            ),
            ytdlp=self._check_ytdlp(),
            cookies=self._check_cookies_file(),
            downloads_dir=self._check_downloads_dir(downloads_dir=downloads_dir),
        )

        logger.info(
            "Environment checked. ffmpeg={} deno={} ytdlp={} cookies={} downloads_dir={}",
            format_environment_item_for_log(status.ffmpeg),
            format_environment_item_for_log(status.deno),
            format_environment_item_for_log(status.ytdlp),
            format_environment_item_for_log(status.cookies),
            format_environment_item_for_log(status.downloads_dir),
        )

        return status

    def _check_executable(
        self,
        *,
        title: str,
        executable_name: str,
        missing_message: str,
    ) -> EnvironmentItemStatus:
        executable_path = self.process_runner.find_executable(executable_name)

        if executable_path is None:
            return EnvironmentItemStatus(
                title=title,
                is_ok=False,
                message=missing_message,
            )

        return EnvironmentItemStatus(
            title=title,
            is_ok=True,
            message="найден",
            path=executable_path,
        )

    def _check_ytdlp(self) -> EnvironmentItemStatus:
        try:
            version = importlib.metadata.version("yt-dlp")
        except importlib.metadata.PackageNotFoundError:
            return EnvironmentItemStatus(
                title="yt-dlp",
                is_ok=False,
                message="не найден",
            )

        return EnvironmentItemStatus(
            title="yt-dlp",
            is_ok=True,
            message=version,
        )

    def _check_cookies_file(self) -> EnvironmentItemStatus:
        cookies_file = self.paths.cookies_file

        if not cookies_file.is_file():
            return EnvironmentItemStatus(
                title="cookies.txt",
                is_ok=False,
                message="не найден",
                path=cookies_file,
            )

        try:
            first_line = cookies_file.read_text(encoding="utf-8", errors="replace").splitlines()[0]
        except (OSError, IndexError):
            return EnvironmentItemStatus(
                title="cookies.txt",
                is_ok=False,
                message="пустой или недоступен",
                path=cookies_file,
            )

        if not first_line.startswith(COOKIES_HEADER_PREFIXES):
            return EnvironmentItemStatus(
                title="cookies.txt",
                is_ok=False,
                message="подозрительный формат",
                path=cookies_file,
            )

        return EnvironmentItemStatus(
            title="cookies.txt",
            is_ok=True,
            message=f"{cookies_file.stat().st_size} байт",
            path=cookies_file,
        )

    def _check_downloads_dir(self, *, downloads_dir: Path) -> EnvironmentItemStatus:
        try:
            downloads_dir.mkdir(parents=True, exist_ok=True)
            probe_file = downloads_dir / f".yaloader_write_test_{uuid4().hex}.tmp"
            probe_file.write_text("ok", encoding="utf-8")
            probe_file.unlink()
        except OSError as error:
            return EnvironmentItemStatus(
                title="Папка загрузок",
                is_ok=False,
                message=f"нет записи: {error}",
                path=downloads_dir,
            )

        return EnvironmentItemStatus(
            title="Папка загрузок",
            is_ok=True,
            message="доступна",
            path=downloads_dir,
        )


def format_environment_item_for_log(status: EnvironmentItemStatus) -> str:
    state = "ok" if status.is_ok else "warning"

    if status.path is None:
        return f"{status.title}={state}:{status.message}"

    return f"{status.title}={state}:{status.message}; path={status.path}"
