from __future__ import annotations

from PyQt6.QtCore import QRect

from yaloader.ui.widgets.download_queue.table import build_queue_empty_hint_label_rect


def test_build_queue_empty_hint_label_rect_uses_viewport_geometry() -> None:
    rect = build_queue_empty_hint_label_rect(
        viewport_geometry=QRect(10, 20, 400, 300),
    )

    assert rect == QRect(46, 56, 328, 228)


def test_build_queue_empty_hint_label_rect_omits_margin_for_small_viewport() -> None:
    rect = build_queue_empty_hint_label_rect(
        viewport_geometry=QRect(10, 20, 40, 20),
    )

    assert rect == QRect(10, 20, 40, 20)
