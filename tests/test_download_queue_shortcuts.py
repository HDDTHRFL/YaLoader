from __future__ import annotations

from PyQt6.QtCore import Qt

from yaloader.ui.widgets.download_queue.table import (
    is_clear_queue_key_event,
    is_remove_selected_tasks_key_event,
)


class FakeKeyEvent:
    def __init__(self, *, key: Qt.Key, modifiers: Qt.KeyboardModifier) -> None:
        self._key = key
        self._modifiers = modifiers

    def key(self) -> Qt.Key:
        return self._key

    def modifiers(self) -> Qt.KeyboardModifier:
        return self._modifiers


def test_delete_is_remove_selected_tasks_shortcut() -> None:
    event = FakeKeyEvent(
        key=Qt.Key.Key_Delete,
        modifiers=Qt.KeyboardModifier.NoModifier,
    )

    assert is_remove_selected_tasks_key_event(event=event) is True
    assert is_clear_queue_key_event(event=event) is False


def test_shift_delete_is_clear_queue_shortcut() -> None:
    event = FakeKeyEvent(
        key=Qt.Key.Key_Delete,
        modifiers=Qt.KeyboardModifier.ShiftModifier,
    )

    assert is_clear_queue_key_event(event=event) is True
    assert is_remove_selected_tasks_key_event(event=event) is False


def test_other_key_is_not_queue_shortcut() -> None:
    event = FakeKeyEvent(
        key=Qt.Key.Key_Backspace,
        modifiers=Qt.KeyboardModifier.NoModifier,
    )

    assert is_remove_selected_tasks_key_event(event=event) is False
    assert is_clear_queue_key_event(event=event) is False
