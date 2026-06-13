from __future__ import annotations

from yaloader.ui.widgets.app_header import VERSION_LABEL_PREFIX, format_app_version_label


def test_format_app_version_label_adds_version_prefix() -> None:
    assert format_app_version_label(version="1.0.0") == "_ 1.0.0"


def test_format_app_version_label_strips_spaces() -> None:
    assert format_app_version_label(version=" 1.0.1 ") == "_ 1.0.1"


def test_format_app_version_label_handles_empty_version() -> None:
    assert format_app_version_label(version=" ") == VERSION_LABEL_PREFIX
