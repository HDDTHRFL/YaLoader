from __future__ import annotations

from yaloader.application.services.app_update_service import AppUpdateService


class FakeAppUpdateChecker:
    def __init__(
        self, *, latest_version: str | None = None, error: Exception | None = None
    ) -> None:
        self._latest_version = latest_version
        self._error = error

    def get_latest_version(self) -> str:
        if self._error is not None:
            raise self._error

        if self._latest_version is None:
            raise RuntimeError("latest version is not configured")

        return self._latest_version


def test_app_update_service_reports_available_update() -> None:
    service = AppUpdateService(
        current_version="1.0.0",
        checker=FakeAppUpdateChecker(latest_version="1.1.0"),
    )

    result = service.check_update()

    assert result.should_update is True
    assert result.latest_version == "1.1.0"
    assert "Доступна новая версия" in result.message


def test_app_update_service_reports_up_to_date_version() -> None:
    service = AppUpdateService(
        current_version="1.1.0",
        checker=FakeAppUpdateChecker(latest_version="1.1.0"),
    )

    result = service.check_update()

    assert result.should_update is False
    assert result.is_success is True
    assert result.message == "YaLoader актуален: 1.1.0"


def test_app_update_service_reports_check_failure() -> None:
    service = AppUpdateService(
        current_version="1.0.0",
        checker=FakeAppUpdateChecker(error=RuntimeError("network is unavailable")),
    )

    result = service.check_update()

    assert result.is_success is False
    assert "network is unavailable" in result.message
