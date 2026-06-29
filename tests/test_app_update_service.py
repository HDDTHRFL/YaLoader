from __future__ import annotations

from yaloader.application.dto.app_update import (
    AppReleaseInfo,
    AppUpdateInstallResult,
)
from yaloader.application.services.app_update_service import AppUpdateService


class FakeAppUpdateChecker:
    def __init__(
        self,
        *,
        release_info: AppReleaseInfo | None = None,
        error: Exception | None = None,
    ) -> None:
        self._release_info = release_info
        self._error = error

    def get_latest_release(self) -> AppReleaseInfo:
        if self._error is not None:
            raise self._error

        if self._release_info is None:
            raise RuntimeError("latest release is not configured")

        return self._release_info


class FakeAppUpdateInstaller:
    def __init__(self) -> None:
        self.installed_release_info: AppReleaseInfo | None = None

    def install(self, *, release_info: AppReleaseInfo) -> AppUpdateInstallResult:
        self.installed_release_info = release_info
        return AppUpdateInstallResult.ready_to_restart(
            installed_version=release_info.version,
        )


def test_app_update_service_reports_available_update() -> None:
    release_info = AppReleaseInfo(
        version="1.1.0",
        archive_name="YaLoader-v1.1.0-windows-x64.zip",
        archive_url="https://example.test/YaLoader-v1.1.0-windows-x64.zip",
        archive_sha256="a" * 64,
    )
    service = AppUpdateService(
        current_version="1.0.0",
        checker=FakeAppUpdateChecker(release_info=release_info),
        installer=FakeAppUpdateInstaller(),
    )

    result = service.check_update()

    assert result.should_update is True
    assert result.latest_version == "1.1.0"
    assert result.release_info == release_info
    assert result.release_info.has_update_assets is True
    assert "Доступна новая версия" in result.message


def test_app_update_service_reports_up_to_date_version() -> None:
    release_info = AppReleaseInfo(version="1.1.0")
    service = AppUpdateService(
        current_version="1.1.0",
        checker=FakeAppUpdateChecker(release_info=release_info),
        installer=FakeAppUpdateInstaller(),
    )

    result = service.check_update()

    assert result.should_update is False
    assert result.is_success is True
    assert result.message == "YaLoader актуален: 1.1.0"


def test_app_update_service_reports_check_failure() -> None:
    service = AppUpdateService(
        current_version="1.0.0",
        checker=FakeAppUpdateChecker(error=RuntimeError("network is unavailable")),
        installer=FakeAppUpdateInstaller(),
    )

    result = service.check_update()

    assert result.is_success is False
    assert "network is unavailable" in result.message


def test_app_update_service_delegates_installation_to_installer() -> None:
    release_info = AppReleaseInfo(version="1.1.0")
    installer = FakeAppUpdateInstaller()
    service = AppUpdateService(
        current_version="1.0.0",
        checker=FakeAppUpdateChecker(release_info=release_info),
        installer=installer,
    )

    result = service.install_update(release_info=release_info)

    assert result.should_restart is True
    assert installer.installed_release_info == release_info
