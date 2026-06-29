from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from loguru import logger

from yaloader.application.dto.environment_status import EnvironmentItemStatus, EnvironmentStatus
from yaloader.application.dto.ytdlp_runtime import YtDlpRuntimeInfo, YtDlpRuntimeSource
from yaloader.application.ports.process_runner import ProcessRunner
from yaloader.application.ports.ytdlp_runtime import YtDlpRuntimeInfoProvider
from yaloader.application.services.cookies_file_service import (
    CookiesFileImportError,
    format_cookies_file_size,
    is_large_cookies_file,
    validate_cookies_file,
)
from yaloader.config.paths import AppPaths


@dataclass(frozen=True, slots=True)
class PackageYtDlpRuntimeInfoProvider:
    def get_runtime_info(self) -> YtDlpRuntimeInfo:
        try:
            version = importlib.metadata.version("yt-dlp")
        except importlib.metadata.PackageNotFoundError as error:
            raise RuntimeError("yt-dlp не найден") from error

        return YtDlpRuntimeInfo.bundled(version=version)


@dataclass(frozen=True, slots=True)
class EnvironmentCheckService:
    paths: AppPaths
    process_runner: ProcessRunner
    ytdlp_runtime_provider: YtDlpRuntimeInfoProvider = field(
        default_factory=PackageYtDlpRuntimeInfoProvider,
    )

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
            runtime_info = self.ytdlp_runtime_provider.get_runtime_info()
        except Exception as error:
            return EnvironmentItemStatus(
                title="yt-dlp",
                is_ok=False,
                message=str(error),
            )

        return EnvironmentItemStatus(
            title="yt-dlp",
            is_ok=True,
            message=format_ytdlp_runtime_status(runtime_info=runtime_info),
            path=runtime_info.path,
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
            size_bytes = cookies_file.stat().st_size
        except OSError as error:
            return EnvironmentItemStatus(
                title="cookies.txt",
                is_ok=False,
                message=f"недоступен: {error}",
                path=cookies_file,
            )

        try:
            if is_large_cookies_file(source_file=cookies_file):
                return EnvironmentItemStatus(
                    title="cookies.txt",
                    is_ok=False,
                    message=f"слишком большой: {format_cookies_file_size(size_bytes=size_bytes)}",
                    path=cookies_file,
                )

            validate_cookies_file(source_file=cookies_file)
        except CookiesFileImportError as error:
            return EnvironmentItemStatus(
                title="cookies.txt",
                is_ok=False,
                message=str(error),
                path=cookies_file,
            )

        return EnvironmentItemStatus(
            title="cookies.txt",
            is_ok=True,
            message=format_cookies_file_size(size_bytes=size_bytes),
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


def format_ytdlp_runtime_status(*, runtime_info: YtDlpRuntimeInfo) -> str:
    if runtime_info.source is YtDlpRuntimeSource.EXTERNAL:
        return f"{runtime_info.version} (пользовательский)"

    if runtime_info.fallback_reason is not None:
        return f"{runtime_info.version} (встроенный | внешний отключён)"

    return f"{runtime_info.version} (встроенный)"


def format_environment_item_for_log(status: EnvironmentItemStatus) -> str:
    state = "ok" if status.is_ok else "warning"

    if status.path is None:
        return f"{status.title}={state}:{status.message}"

    return f"{status.title}={state}:{status.message}; path={status.path}"
