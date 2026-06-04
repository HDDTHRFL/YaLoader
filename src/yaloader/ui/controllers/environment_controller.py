from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from yaloader.application.dto.app_settings import AppSettings
from yaloader.application.dto.environment_status import EnvironmentStatus
from yaloader.application.services.environment_check_service import EnvironmentCheckService
from yaloader.application.services.settings_service import SettingsService
from yaloader.config.paths import AppPaths
from yaloader.domain.download_speed_limit import format_download_speed_limit_label


@dataclass(frozen=True, slots=True)
class EnvironmentControllerUpdate:
    status_message: str | None = None
    settings: AppSettings | None = None
    environment_status: EnvironmentStatus | None = None
    directory_to_open: Path | None = None
    should_play_refresh_feedback: bool = False


class EnvironmentController:
    def __init__(
        self,
        *,
        paths: AppPaths,
        settings_service: SettingsService,
        environment_check_service: EnvironmentCheckService,
    ) -> None:
        self._paths = paths
        self._settings_service = settings_service
        self._environment_check_service = environment_check_service

    def load_status(self, *, downloads_dir: Path) -> EnvironmentControllerUpdate:
        return EnvironmentControllerUpdate(
            environment_status=self._check_environment(downloads_dir=downloads_dir),
        )

    def refresh_status(self, *, downloads_dir: Path) -> EnvironmentControllerUpdate:
        return EnvironmentControllerUpdate(
            status_message="Состояние системы обновлено",
            environment_status=self._check_environment(downloads_dir=downloads_dir),
            should_play_refresh_feedback=True,
        )

    def change_downloads_dir(self, *, downloads_dir: Path) -> EnvironmentControllerUpdate:
        if not downloads_dir.is_absolute():
            return EnvironmentControllerUpdate(
                status_message="Папка загрузок должна быть абсолютным путём",
            )

        try:
            downloads_dir.mkdir(parents=True, exist_ok=True)
            settings = self._settings_service.update_downloads_dir(
                downloads_dir=downloads_dir,
            )
        except (OSError, ValidationError) as error:
            return EnvironmentControllerUpdate(
                status_message=f"Не удалось изменить папку загрузок: {error}",
            )

        return EnvironmentControllerUpdate(
            status_message=f"Папка загрузок изменена: {settings.downloads_dir}",
            settings=settings,
            environment_status=self._check_environment(downloads_dir=settings.downloads_dir),
        )

    def change_download_speed_limit(
        self,
        *,
        bytes_per_second: int | None,
    ) -> EnvironmentControllerUpdate:
        try:
            settings = self._settings_service.update_download_speed_limit(
                bytes_per_second=bytes_per_second,
            )
        except (ValueError, ValidationError) as error:
            return EnvironmentControllerUpdate(
                status_message=f"Не удалось изменить ограничение скорости: {error}",
            )

        return EnvironmentControllerUpdate(
            status_message=(
                "Ограничение скорости загрузки: "
                f"{format_download_speed_limit_label(bytes_per_second=bytes_per_second)}"
            ),
            settings=settings,
        )

    def delete_cookies(self, *, downloads_dir: Path) -> EnvironmentControllerUpdate:
        cookies_file = self._paths.cookies_file

        if not cookies_file.is_file():
            return EnvironmentControllerUpdate(
                status_message=f"cookies.txt не найден: {cookies_file}",
                environment_status=self._check_environment(downloads_dir=downloads_dir),
            )

        try:
            cookies_file.unlink()
        except OSError as error:
            return EnvironmentControllerUpdate(
                status_message=f"Не удалось удалить cookies.txt: {error}",
                environment_status=self._check_environment(downloads_dir=downloads_dir),
            )

        return EnvironmentControllerUpdate(
            status_message=f"cookies.txt удалён безвозвратно: {cookies_file}",
            environment_status=self._check_environment(downloads_dir=downloads_dir),
        )

    def open_cookies_dir(self) -> EnvironmentControllerUpdate:
        try:
            self._paths.data_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            return EnvironmentControllerUpdate(
                status_message=f"Не удалось открыть папку cookies: {error}",
            )

        return EnvironmentControllerUpdate(directory_to_open=self._paths.data_dir)

    def open_downloads_dir(self, *, downloads_dir: Path) -> EnvironmentControllerUpdate:
        try:
            downloads_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            return EnvironmentControllerUpdate(
                status_message=f"Не удалось открыть папку загрузок: {error}",
            )

        return EnvironmentControllerUpdate(directory_to_open=downloads_dir)

    def _check_environment(self, *, downloads_dir: Path) -> EnvironmentStatus:
        return self._environment_check_service.check(downloads_dir=downloads_dir)
