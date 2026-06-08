from __future__ import annotations

from yaloader.ui.main_window import (
    HISTORY_PANEL_WIDTH,
    WINDOW_MINIMUM_WIDTH,
    calculate_history_adjusted_window_minimum_width,
)


def test_calculate_history_adjusted_window_minimum_width_without_history() -> None:
    assert (
        calculate_history_adjusted_window_minimum_width(history_panel_width=0)
        == WINDOW_MINIMUM_WIDTH
    )


def test_calculate_history_adjusted_window_minimum_width_with_history() -> None:
    assert (
        calculate_history_adjusted_window_minimum_width(
            history_panel_width=HISTORY_PANEL_WIDTH,
        )
        == WINDOW_MINIMUM_WIDTH + HISTORY_PANEL_WIDTH
    )


def test_calculate_history_adjusted_window_minimum_width_ignores_negative_width() -> None:
    assert (
        calculate_history_adjusted_window_minimum_width(history_panel_width=-100)
        == WINDOW_MINIMUM_WIDTH
    )
