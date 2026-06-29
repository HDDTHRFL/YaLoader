from __future__ import annotations

from typing import Protocol

from yaloader.application.dto.app_update import AppReleaseInfo


class AppUpdateChecker(Protocol):
    def get_latest_release(self) -> AppReleaseInfo: ...
