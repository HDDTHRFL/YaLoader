from __future__ import annotations

from yaloader.ui.widgets.app_header import format_app_version_label_with_update


def test_format_app_version_label_with_update_contains_clickable_release_link() -> None:
    label = format_app_version_label_with_update(
        current_version="1.0.0",
        latest_version="1.1.0",
        releases_url="https://github.com/HDDTHRFL/YaLoader/releases",
    )

    assert "_ 1.0.0" in label
    assert "[доступна новая версия]" in label
    assert "https://github.com/HDDTHRFL/YaLoader/releases" in label
    assert "Доступна версия 1.1.0" in label
