from __future__ import annotations

from yaloader.ui.widgets.download_queue.panel import (
    CLEAR_DOWNLOAD_QUEUE_TOOLTIP,
    REMOVE_SELECTED_QUEUE_ITEMS_TOOLTIP,
)


def test_download_queue_button_tooltips_describe_keyboard_shortcuts() -> None:
    assert REMOVE_SELECTED_QUEUE_ITEMS_TOOLTIP == "клавиша Delete"
    assert CLEAR_DOWNLOAD_QUEUE_TOOLTIP == "сочетание клавиш Shift + Delete"
