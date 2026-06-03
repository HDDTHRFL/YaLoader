from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from yaloader.config.app_info import APP_DISPLAY_NAME

HISTORY_TOGGLE_BUTTON_SIZE = 36
SETTINGS_BUTTON_SIZE = 34

TITLE_FONT_FAMILY = "Death Stars"
TITLE_FONT_POINT_SIZE = 40
TITLE_LETTER_SPACING_PERCENT = 112.0

SUBTITLE_TEXT = "Загрузка видео и аудио в максимальном доступном качестве"


class AppHeader(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.history_toggle_button = QPushButton("›", self)
        self.settings_button = QPushButton("🛠", self)

        self._configure_widgets()
        self._build_layout()

    def set_history_visible(self, *, is_visible: bool) -> None:
        self.history_toggle_button.setText("‹" if is_visible else "›")

    def _configure_widgets(self) -> None:
        self.history_toggle_button.setObjectName("DrawerToggleButton")
        self.history_toggle_button.setFixedSize(
            HISTORY_TOGGLE_BUTTON_SIZE,
            HISTORY_TOGGLE_BUTTON_SIZE,
        )
        self.history_toggle_button.setToolTip("Показать или скрыть историю загрузок")

        self.settings_button.setObjectName("IconButton")
        self.settings_button.setFixedSize(
            SETTINGS_BUTTON_SIZE,
            SETTINGS_BUTTON_SIZE,
        )
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.setToolTip("Настройки загрузки")

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(4)

        title_row_layout = QHBoxLayout()
        title_row_layout.setContentsMargins(0, 0, 0, 0)
        title_row_layout.setSpacing(12)

        subtitle_row_layout = QHBoxLayout()
        subtitle_row_layout.setContentsMargins(0, 0, 0, 0)
        subtitle_row_layout.setSpacing(12)

        title_label = self._build_title_label()
        subtitle_label = QLabel(SUBTITLE_TEXT, self)
        subtitle_label.setObjectName("SubtitleLabel")

        title_row_layout.addWidget(
            title_label,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        title_row_layout.addStretch(1)
        title_row_layout.addWidget(
            self.history_toggle_button,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        subtitle_row_layout.addWidget(
            subtitle_label,
            stretch=1,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        subtitle_row_layout.addWidget(
            self.settings_button,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        root_layout.addLayout(title_row_layout)
        root_layout.addLayout(subtitle_row_layout)

    def _build_title_label(self) -> QLabel:
        title_label = QLabel(APP_DISPLAY_NAME, self)
        title_label.setObjectName("TitleLabel")

        title_font = QFont(TITLE_FONT_FAMILY)
        title_font.setPointSize(TITLE_FONT_POINT_SIZE)
        title_font.setWeight(QFont.Weight.Normal)
        title_font.setLetterSpacing(
            QFont.SpacingType.PercentageSpacing,
            TITLE_LETTER_SPACING_PERCENT,
        )
        title_label.setFont(title_font)

        return title_label
