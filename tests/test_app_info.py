from __future__ import annotations

from yaloader.config.app_info import (
    APP_VERSION,
    UNKNOWN_APP_VERSION,
    resolve_application_version,
)


def test_resolve_application_version_returns_unknown_for_missing_package() -> None:
    assert resolve_application_version(package_name="definitely-missing-yaloader-package") == UNKNOWN_APP_VERSION


def test_app_version_is_resolved_from_package_metadata() -> None:
    assert APP_VERSION
    assert APP_VERSION != UNKNOWN_APP_VERSION
