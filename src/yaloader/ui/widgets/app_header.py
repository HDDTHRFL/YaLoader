from __future__ import annotations

import html
from typing import Final, override

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QResizeEvent
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from yaloader.config.app_info import APP_DISPLAY_NAME, APP_VERSION
from yaloader.ui.font_loading import FALLBACK_TITLE_FONT_FAMILY

HISTORY_TOGGLE_BUTTON_SIZE: Final = 36
SETTINGS_BUTTON_SIZE: Final = 42

TITLE_FONT_POINT_SIZE: Final = 40
TITLE_LETTER_SPACING_PERCENT: Final = 112.0
TITLE_LABEL_FIXED_HEIGHT: Final = 54

HEADER_TOP_MARGIN: Final = 10
TITLE_TO_SUBTITLE_SPACING: Final = 8
HEADER_BOTTOM_MARGIN: Final = 8

TITLE_ROW_SPACING: Final = 8
SUBTITLE_ROW_SPACING: Final = 0

HISTORY_BUTTON_RIGHT_RESERVED_WIDTH: Final = HISTORY_TOGGLE_BUTTON_SIZE
HISTORY_BUTTON_TITLE_CENTER_OFFSET: Final = -6

SETTINGS_BUTTON_RIGHT_RESERVED_WIDTH: Final = SETTINGS_BUTTON_SIZE
SETTINGS_BUTTON_SUBTITLE_BOTTOM_OFFSET: Final = 0

VERSION_LABEL_PREFIX: Final = "_ "
VERSION_FONT_POINT_SIZE: Final = 8
VERSION_LETTER_SPACING_PERCENT: Final = 108.0
APP_UPDATE_LINK_HREF: Final = "yaloader://install-update"
APP_UPDATE_LINK_TEXT: Final = "доступна новая версия"
APP_UPDATE_LINK_COLOR: Final = "#FCD34D"

TITLE_FONT_FALLBACKS: Final = (
    "Death Stars",
    "Segoe UI Black",
    "Arial Black",
)

SUBTITLE_TEXT: Final = "Загрузка видео и аудио в максимальном доступном качестве"


class AppHeader(QWidget):
    app_update_requested = pyqtSignal()

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
        self._version_label = QLabel(format_app_version_label(version=APP_VERSION), self)
        self._subtitle_label = QLabel(SUBTITLE_TEXT, self)

        self._configure_widgets()
        self._build_layout()

    def set_history_visible(self, *, is_visible: bool) -> None:
        self.history_toggle_button.setText("‹" if is_visible else "›")

    def set_application_update_available(
        self,
        *,
        latest_version: str,
        releases_url: str,
    ) -> None:
        self._version_label.setTextFormat(Qt.TextFormat.RichText)
        self._version_label.setOpenExternalLinks(False)
        self._version_label.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self._version_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._version_label.setToolTip(f"Обновить YaLoader до версии {latest_version}. Страница релиза: {releases_url}")
        self._version_label.setText(
            format_app_version_label_with_update(
                current_version=APP_VERSION,
                latest_version=latest_version,
            )
        )

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
        self._title_label.setStyleSheet(build_title_label_style_sheet(title_font_family=self._title_font_family))

        self._version_label.setObjectName("VersionLabel")
        self._version_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )
        self._version_label.setFont(self._build_version_font())
        self._version_label.setStyleSheet(build_version_label_style_sheet(title_font_family=self._title_font_family))
        self._version_label.linkActivated.connect(self._handle_version_link_activated)

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
            stretch=0,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )
        title_row_layout.addWidget(
            self._version_label,
            stretch=0,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        )
        title_row_layout.addStretch(1)

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

    def _build_version_font(self) -> QFont:
        version_font = QFont(self._title_font_family)
        version_font.setPointSize(VERSION_FONT_POINT_SIZE)
        version_font.setWeight(QFont.Weight.Normal)
        version_font.setLetterSpacing(
            QFont.SpacingType.PercentageSpacing,
            VERSION_LETTER_SPACING_PERCENT,
        )

        return version_font

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

    def _handle_version_link_activated(self, link: str) -> None:
        if link != APP_UPDATE_LINK_HREF:
            return

        self.app_update_requested.emit()


def format_app_version_label(*, version: str) -> str:
    normalized_version = version.strip()

    if not normalized_version:
        return VERSION_LABEL_PREFIX

    return f"{VERSION_LABEL_PREFIX}{normalized_version}"


def format_app_version_label_with_update(
    *,
    current_version: str,
    latest_version: str,
) -> str:
    base_label = html.escape(format_app_version_label(version=current_version))
    safe_latest_version = html.escape(latest_version)

    return (
        f'{base_label} <a href="{APP_UPDATE_LINK_HREF}" '
        f'style="color: {APP_UPDATE_LINK_COLOR}; text-decoration: underline;" '
        f'title="Обновить до версии {safe_latest_version}">'
        f"[{APP_UPDATE_LINK_TEXT}]</a>"
    )


def build_title_label_style_sheet(*, title_font_family: str) -> str:
    return (
        "QLabel#TitleLabel {"
        f"font-family: {build_title_font_family_stack(title_font_family=title_font_family)};"
        "color: #FFFFFF;"
        "}"
    )


def build_version_label_style_sheet(*, title_font_family: str) -> str:
    return (
        "QLabel#VersionLabel {"
        f"font-family: {build_title_font_family_stack(title_font_family=title_font_family)};"
        f"font-size: {VERSION_FONT_POINT_SIZE}pt;"
        "font-weight: 400;"
        "color: #6E7681;"
        "}"
    )


def build_title_font_family_stack(*, title_font_family: str) -> str:
    font_families = (
        title_font_family,
        *TITLE_FONT_FALLBACKS,
    )

    return ", ".join(
        f'"{escape_qss_font_family(value=font_family)}"' for font_family in font_families if font_family.strip()
    )


def escape_qss_font_family(*, value: str) -> str:
    normalized_value = value.strip()

    if not normalized_value:
        return FALLBACK_TITLE_FONT_FAMILY

    return normalized_value.replace("\\", "\\\\").replace('"', '\\"')
