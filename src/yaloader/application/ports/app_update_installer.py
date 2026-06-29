from __future__ import annotations

from typing import Protocol

from yaloader.application.dto.app_update import AppReleaseInfo, AppUpdateInstallResult


class AppUpdateInstaller(Protocol):
    def install(self, *, release_info: AppReleaseInfo) -> AppUpdateInstallResult: ...
