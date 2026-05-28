from __future__ import annotations

import sys

from PyQt6.QtGui import QFontDatabase, QIcon
from PyQt6.QtWidgets import QApplication

from yaloader.config.app_info import APP_DISPLAY_NAME, APP_NAME, APP_VERSION, ORGANIZATION_NAME
from yaloader.config.resources import get_app_icon_path, get_title_font_path
from yaloader.services.app_container import AppContainer
from yaloader.ui.main_window import MainWindow
from yaloader.ui.styles import APP_STYLE_SHEET


def run_gui_application(container: AppContainer) -> int:
    application = QApplication(sys.argv.copy())
    application.setApplicationName(APP_NAME)
    application.setApplicationDisplayName(APP_DISPLAY_NAME)
    application.setApplicationVersion(APP_VERSION)
    application.setOrganizationName(ORGANIZATION_NAME)

    load_application_fonts()
    application.setStyleSheet(APP_STYLE_SHEET)

    app_icon = build_app_icon()

    if not app_icon.isNull():
        application.setWindowIcon(app_icon)

    window = MainWindow(container=container)

    if not app_icon.isNull():
        window.setWindowIcon(app_icon)

    window.show()

    return application.exec()


def build_app_icon() -> QIcon:
    icon_path = get_app_icon_path()

    if not icon_path.is_file():
        return QIcon()

    return QIcon(str(icon_path))


def load_application_fonts() -> None:
    title_font_path = get_title_font_path()

    if not title_font_path.is_file():
        return

    QFontDatabase.addApplicationFont(str(title_font_path))
