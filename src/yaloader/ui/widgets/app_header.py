from __future__ import annotations

from typing import override

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QResizeEvent
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from yaloader.config.app_info import APP_DISPLAY_NAME
from yaloader.ui.font_loading import FALLBACK_TITLE_FONT_FAMILY

HISTORY_TOGGLE_BUTTON_SIZE = 36
SETTINGS_BUTTON_SIZE = 42

TITLE_FONT_POINT_SIZE = 40
TITLE_LETTER_SPACING_PERCENT = 112.0
TITLE_LABEL_FIXED_HEIGHT = 54

HEADER_TOP_MARGIN = 10
TITLE_TO_SUBTITLE_SPACING = 8
HEADER_BOTTOM_MARGIN = 8

TITLE_ROW_SPACING = 0
SUBTITLE_ROW_SPACING = 0

HISTORY_BUTTON_RIGHT_RESERVED_WIDTH = HISTORY_TOGGLE_BUTTON_SIZE
HISTORY_BUTTON_TITLE_CENTER_OFFSET = -6

SETTINGS_BUTTON_RIGHT_RESERVED_WIDTH = SETTINGS_BUTTON_SIZE
SETTINGS_BUTTON_SUBTITLE_BOTTOM_OFFSET = 0

TITLE_FONT_FALLBACKS = (
    "Death Stars",
    "Segoe UI Black",
    "Arial Black",
)

SUBTITLE_TEXT = "Загрузка видео и аудио в максимальном доступном качестве"


class AppHeader(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        title_font_family: str = FALLBACK_TITLE_FONT_FAMILY,
    ) -> None:
        super().__init__(parent)

        self._title_font_family = title_font_family

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
        self._position_history_toggle_button()
        self._position_settings_button()

    def _configure_widgets(self) -> None:
        self.history_toggle_button.setObjectName("DrawerToggleButton")
        self.history_toggle_button.setFixedSize(
            HISTORY_TOGGLE_BUTTON_SIZE,
            HISTORY_TOGGLE_BUTTON_SIZE,
        )
        self.history_toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_toggle_button.setToolTip("Показать или скрыть историю загрузок")

        self.settings_button.setObjectName("SettingsToolButton")
        self.settings_button.setFixedSize(
            SETTINGS_BUTTON_SIZE,
            SETTINGS_BUTTON_SIZE,
        )
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.setToolTip("Показать или скрыть настройки")

        self._title_label.setObjectName("TitleLabel")
        self._title_label.setFixedHeight(TITLE_LABEL_FIXED_HEIGHT)
        self._title_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )
        self._title_label.setFont(self._build_title_font())
        self._title_label.setStyleSheet(
            build_title_label_style_sheet(title_font_family=self._title_font_family)
        )

        self._subtitle_label.setObjectName("SubtitleLabel")

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            0,
            HEADER_TOP_MARGIN,
            0,
            HEADER_BOTTOM_MARGIN,
        )
        root_layout.setSpacing(TITLE_TO_SUBTITLE_SPACING)

        title_row_layout = QHBoxLayout()
        title_row_layout.setContentsMargins(0, 0, HISTORY_BUTTON_RIGHT_RESERVED_WIDTH, 0)
        title_row_layout.setSpacing(TITLE_ROW_SPACING)

        subtitle_row_layout = QHBoxLayout()
        subtitle_row_layout.setContentsMargins(
            0,
            0,
            SETTINGS_BUTTON_RIGHT_RESERVED_WIDTH,
            0,
        )
        subtitle_row_layout.setSpacing(SUBTITLE_ROW_SPACING)

        title_row_layout.addWidget(
            self._title_label,
            stretch=1,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )

        subtitle_row_layout.addWidget(
            self._subtitle_label,
            stretch=1,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )

        root_layout.addLayout(title_row_layout)
        root_layout.addLayout(subtitle_row_layout)

        self.history_toggle_button.raise_()
        self.settings_button.raise_()
        self._position_history_toggle_button()
        self._position_settings_button()

    def _build_title_font(self) -> QFont:
        title_font = QFont(self._title_font_family)
        title_font.setPointSize(TITLE_FONT_POINT_SIZE)
        title_font.setWeight(QFont.Weight.Normal)
        title_font.setLetterSpacing(
            QFont.SpacingType.PercentageSpacing,
            TITLE_LETTER_SPACING_PERCENT,
        )

        return title_font

    def _position_history_toggle_button(self) -> None:
        title_geometry = self._title_label.geometry()
        title_center_y = title_geometry.y() + title_geometry.height() // 2

        x = max(0, self.width() - HISTORY_TOGGLE_BUTTON_SIZE)
        y = max(
            0,
            title_center_y - HISTORY_TOGGLE_BUTTON_SIZE // 2 + HISTORY_BUTTON_TITLE_CENTER_OFFSET,
        )

        self.history_toggle_button.move(x, y)

    def _position_settings_button(self) -> None:
        subtitle_geometry = self._subtitle_label.geometry()
        subtitle_bottom = subtitle_geometry.y() + subtitle_geometry.height()

        x = max(0, self.width() - SETTINGS_BUTTON_SIZE)
        y = max(
            0,
            subtitle_bottom - SETTINGS_BUTTON_SIZE + SETTINGS_BUTTON_SUBTITLE_BOTTOM_OFFSET,
        )

        self.settings_button.move(x, y)


def build_title_label_style_sheet(*, title_font_family: str) -> str:
    return (
        "QLabel#TitleLabel {"
        f"font-family: {build_title_font_family_stack(title_font_family=title_font_family)};"
        "color: #FFFFFF;"
        "}"
    )


def build_title_font_family_stack(*, title_font_family: str) -> str:
    font_families = (
        title_font_family,
        *TITLE_FONT_FALLBACKS,
    )

    return ", ".join(
        f'"{escape_qss_font_family(value=font_family)}"'
        for font_family in font_families
        if font_family.strip()
    )


def escape_qss_font_family(*, value: str) -> str:
    normalized_value = value.strip()

    if not normalized_value:
        return FALLBACK_TITLE_FONT_FAMILY

    return normalized_value.replace("\\", "\\\\").replace('"', '\\"')
