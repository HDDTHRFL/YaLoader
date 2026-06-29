from __future__ import annotations

from dataclasses import dataclass

from yaloader.application.dto.app_update import (
    GITHUB_RELEASES_URL,
    AppReleaseInfo,
    AppUpdateCheckResult,
    AppUpdateInstallResult,
)
from yaloader.application.ports.app_update_checker import AppUpdateChecker
from yaloader.application.ports.app_update_installer import AppUpdateInstaller
from yaloader.infrastructure.tools.version_detection import is_version_newer


@dataclass(frozen=True, slots=True)
class AppUpdateService:
    current_version: str
    checker: AppUpdateChecker
    installer: AppUpdateInstaller
    releases_url: str = GITHUB_RELEASES_URL

    def check_update(self) -> AppUpdateCheckResult:
        try:
            release_info = self.checker.get_latest_release()
        except Exception as error:
            return AppUpdateCheckResult.check_failed(
                current_version=self.current_version,
                releases_url=self.releases_url,
                message=f"Не удалось проверить обновление YaLoader: {error}",
            )

        try:
            has_update = is_version_newer(
                candidate_version=release_info.version,
                current_version=self.current_version,
            )
        except Exception as error:
            return AppUpdateCheckResult.check_failed(
                current_version=self.current_version,
                releases_url=self.releases_url,
                message=f"Не удалось сравнить версии YaLoader: {error}",
            )

        if has_update:
            return AppUpdateCheckResult.update_available(
                current_version=self.current_version,
                release_info=release_info,
            )

        return AppUpdateCheckResult.up_to_date(
            current_version=self.current_version,
            release_info=release_info,
        )

    def install_update(self, *, release_info: AppReleaseInfo) -> AppUpdateInstallResult:
        return self.installer.install(release_info=release_info)
