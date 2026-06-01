from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMenu, QPushButton, QWidget, QWidgetAction


def create_context_menu(*, parent: QWidget) -> QMenu:
    context_menu = QMenu(parent)
    context_menu.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    return context_menu


def add_menu_button_action(
    *,
    menu: QMenu,
    text: str,
    object_name: str,
) -> QWidgetAction:
    action = QWidgetAction(menu)
    button = QPushButton(text, menu)
    button.setObjectName(object_name)
    button.setCursor(Qt.CursorShape.PointingHandCursor)

    def handle_button_clicked(_checked: bool = False) -> None:
        action.trigger()
        menu.close()

    button.clicked.connect(handle_button_clicked)

    action.setDefaultWidget(button)
    menu.addAction(action)

    return action
