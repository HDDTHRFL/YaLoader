from __future__ import annotations

from typing import override

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QResizeEvent
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from yaloader.config.app_info import APP_DISPLAY_NAME

HISTORY_TOGGLE_BUTTON_SIZE = 36
SETTINGS_BUTTON_SIZE = 42
SETTINGS_BUTTON_VERTICAL_OFFSET = 4

TITLE_FONT_FAMILY = "Death Stars"
TITLE_FONT_POINT_SIZE = 40
TITLE_LETTER_SPACING_PERCENT = 112.0

SUBTITLE_TEXT = "Загрузка видео и аудио в максимальном доступном качестве"


class AppHeader(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.history_toggle_button = QPushButton("›", self)
        self.settings_button = QPushButton("🛠", self)
        self._title_label = QLabel(APP_DISPLAY_NAME, self)
        self._subtitle_label = QLabel(SUBTITLE_TEXT, self)

        self._configure_widgets()
        self._build_layout()

    def set_history_visible(self, *, is_visible: bool) -> None:
        self.history_toggle_button.setText("‹" if is_visible else "›")

    @override
    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._position_settings_button()

    def _configure_widgets(self) -> None:
        self.history_toggle_button.setObjectName("DrawerToggleButton")
        self.history_toggle_button.setFixedSize(
            HISTORY_TOGGLE_BUTTON_SIZE,
            HISTORY_TOGGLE_BUTTON_SIZE,
        )
        self.history_toggle_button.setToolTip("Показать или скрыть историю загрузок")

        self.settings_button.setObjectName("SettingsToolButton")
        self.settings_button.setFixedSize(
            SETTINGS_BUTTON_SIZE,
            SETTINGS_BUTTON_SIZE,
        )
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.setToolTip("Настройки загрузки")

        self._title_label.setObjectName("TitleLabel")
        self._title_label.setFont(self._build_title_font())

        self._subtitle_label.setObjectName("SubtitleLabel")

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(2)

        title_row_layout = QHBoxLayout()
        title_row_layout.setContentsMargins(0, 0, 0, 0)
        title_row_layout.setSpacing(12)

        subtitle_row_layout = QHBoxLayout()
        subtitle_row_layout.setContentsMargins(0, 0, SETTINGS_BUTTON_SIZE, 0)
        subtitle_row_layout.setSpacing(0)

        title_row_layout.addWidget(
            self._title_label,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        title_row_layout.addStretch(1)
        title_row_layout.addWidget(
            self.history_toggle_button,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        subtitle_row_layout.addWidget(
            self._subtitle_label,
            stretch=1,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )

        root_layout.addLayout(title_row_layout)
        root_layout.addLayout(subtitle_row_layout)

        self.settings_button.raise_()

    def _position_settings_button(self) -> None:
        subtitle_geometry = self._subtitle_label.geometry()
        x_position = max(0, self.width() - SETTINGS_BUTTON_SIZE)
        y_position = max(
            0,
            subtitle_geometry.bottom() - SETTINGS_BUTTON_SIZE + SETTINGS_BUTTON_VERTICAL_OFFSET,
        )

        self.settings_button.move(x_position, y_position)
        self.settings_button.raise_()

    def _build_title_font(self) -> QFont:
        title_font = QFont(TITLE_FONT_FAMILY)
        title_font.setPointSize(TITLE_FONT_POINT_SIZE)
        title_font.setWeight(QFont.Weight.Normal)
        title_font.setLetterSpacing(
            QFont.SpacingType.PercentageSpacing,
            TITLE_LETTER_SPACING_PERCENT,
        )

        return title_font
