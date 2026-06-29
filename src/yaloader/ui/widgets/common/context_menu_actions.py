from __future__ import annotations

from typing import override

from PyQt6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QSize, Qt
from PyQt6.QtGui import QEnterEvent, QResizeEvent
from PyQt6.QtWidgets import QLabel, QMenu, QPushButton, QSizePolicy, QWidget, QWidgetAction

MENU_BUTTON_HEIGHT = 32
MENU_BUTTON_LEFT_PADDING = 24
MENU_BUTTON_RIGHT_PADDING = 24
MENU_BUTTON_HOVER_OFFSET = 8
MENU_BUTTON_ANIMATION_DURATION_MS = 95
MENU_MINIMUM_WIDTH = 180

CONTEXT_MENU_STYLE_SHEET = """
QMenu {
    background-color: #161B22;
    color: #F0F3F6;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 6px;
}

QPushButton#MenuButton {
    min-height: 32px;
    padding: 0;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    text-align: left;
}

QPushButton#MenuButton:hover {
    background-color: #1F6FEB;
}

QPushButton#MenuButton:pressed {
    background-color: #174D9E;
}

QPushButton#MenuDangerButton {
    min-height: 32px;
    padding: 0;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    text-align: left;
}

QPushButton#MenuDangerButton:hover {
    background-color: #3A1518;
}

QPushButton#MenuDangerButton:pressed {
    background-color: #4A1116;
}

QPushButton#MenuButton:disabled,
QPushButton#MenuDangerButton:disabled {
    background-color: transparent;
}

QLabel#MenuButtonText {
    color: #F0F3F6;
    background-color: transparent;
    font-weight: 500;
}

QLabel#MenuDangerButtonText {
    color: #FCA5A5;
    background-color: transparent;
    font-weight: 500;
}
"""


class AnimatedMenuButton(QPushButton):
    def __init__(
        self,
        *,
        text: str,
        is_danger: bool,
        parent: QWidget,
    ) -> None:
        super().__init__(parent)

        self._is_danger = is_danger
        self._text = text
        self._text_label = QLabel(text, self)
        self._text_animation = QPropertyAnimation(self._text_label, b"pos", self)

        self._configure_widget()
        self._configure_text_label()
        self._configure_animation()

    @override
    def sizeHint(self) -> QSize:
        text_width = self.fontMetrics().horizontalAdvance(self._text)
        width = max(
            MENU_MINIMUM_WIDTH,
            text_width + MENU_BUTTON_LEFT_PADDING + MENU_BUTTON_RIGHT_PADDING + MENU_BUTTON_HOVER_OFFSET,
        )
        return QSize(width, MENU_BUTTON_HEIGHT)

    @override
    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    @override
    def enterEvent(self, event: QEnterEvent | None) -> None:
        self._animate_text_offset(offset=MENU_BUTTON_HOVER_OFFSET)
        super().enterEvent(event)

    @override
    def leaveEvent(self, event: QEvent | None) -> None:
        self._animate_text_offset(offset=0)
        super().leaveEvent(event)

    @override
    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._sync_text_label_size()

    def _configure_widget(self) -> None:
        self.setObjectName("MenuDangerButton" if self._is_danger else "MenuButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setMinimumSize(self.minimumSizeHint())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _configure_text_label(self) -> None:
        self._text_label.setObjectName("MenuDangerButtonText" if self._is_danger else "MenuButtonText")
        self._text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._text_label.move(MENU_BUTTON_LEFT_PADDING, 0)

    def _configure_animation(self) -> None:
        self._text_animation.setDuration(MENU_BUTTON_ANIMATION_DURATION_MS)
        self._text_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _sync_text_label_size(self) -> None:
        label_width = max(
            0,
            self.width() - MENU_BUTTON_LEFT_PADDING - MENU_BUTTON_RIGHT_PADDING,
        )
        self._text_label.resize(label_width, self.height())

    def _animate_text_offset(self, *, offset: int) -> None:
        self._text_animation.stop()
        self._text_animation.setStartValue(self._text_label.pos())
        self._text_animation.setEndValue(QPoint(MENU_BUTTON_LEFT_PADDING + offset, 0))
        self._text_animation.start()


def create_context_menu(*, parent: QWidget) -> QMenu:
    context_menu = QMenu(parent)
    context_menu.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    context_menu.setMinimumWidth(MENU_MINIMUM_WIDTH)
    context_menu.setStyleSheet(CONTEXT_MENU_STYLE_SHEET)

    return context_menu


def add_menu_action(
    *,
    menu: QMenu,
    text: str,
) -> QWidgetAction:
    return add_menu_button_action(
        menu=menu,
        text=text,
        object_name="MenuButton",
    )


def add_menu_button_action(
    *,
    menu: QMenu,
    text: str,
    object_name: str,
) -> QWidgetAction:
    action = QWidgetAction(menu)
    button = AnimatedMenuButton(
        text=text,
        is_danger=object_name == "MenuDangerButton",
        parent=menu,
    )

    def handle_button_clicked(_checked: bool = False) -> None:
        action.trigger()
        menu.close()

    button.clicked.connect(handle_button_clicked)

    action.setDefaultWidget(button)
    menu.addAction(action)

    return action
