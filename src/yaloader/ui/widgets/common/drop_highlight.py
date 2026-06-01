from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QWidget

DROP_HIGHLIGHT_OBJECT_NAME = "DropHighlightOverlay"

DROP_HIGHLIGHT_STYLE_SHEET = f"""
QFrame#{DROP_HIGHLIGHT_OBJECT_NAME} {{
    background-color: rgba(47, 129, 247, 32);
    border: 1px solid rgba(47, 129, 247, 150);
    border-radius: 10px;
}}
"""


class DropHighlightOverlay(QFrame):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self._configure_widget()

    def set_active(self, *, is_active: bool) -> None:
        self.setVisible(is_active)

        if is_active:
            self.raise_()

    def sync_geometry(self) -> None:
        parent_widget = self.parentWidget()

        if parent_widget is None:
            return

        self.setGeometry(parent_widget.rect())

    def _configure_widget(self) -> None:
        self.setObjectName(DROP_HIGHLIGHT_OBJECT_NAME)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setStyleSheet(DROP_HIGHLIGHT_STYLE_SHEET)
        self.hide()
