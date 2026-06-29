from __future__ import annotations

from yaloader.ui.widgets.app_header import (
    APP_UPDATE_LINK_HREF,
    format_app_version_label_with_update,
)


def test_format_app_version_label_with_update_contains_internal_update_link() -> None:
    label = format_app_version_label_with_update(
        current_version="1.0.0",
        latest_version="1.1.0",
    )

    assert "_ 1.0.0" in label
    assert "[доступна новая версия]" in label
    assert APP_UPDATE_LINK_HREF in label
    assert "Обновить до версии 1.1.0" in label
