from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from yaloader.config.app_info import APP_DISPLAY_NAME, APP_NAME, APP_VERSION, ORGANIZATION_NAME
from yaloader.services.app_container import AppContainer
from yaloader.ui.main_window import MainWindow
from yaloader.ui.styles import APP_STYLE_SHEET


def run_gui_application(container: AppContainer) -> int:
    application = QApplication(sys.argv.copy())
    application.setApplicationName(APP_NAME)
    application.setApplicationDisplayName(APP_DISPLAY_NAME)
    application.setApplicationVersion(APP_VERSION)
    application.setOrganizationName(ORGANIZATION_NAME)
    application.setStyleSheet(APP_STYLE_SHEET)

    window = MainWindow(container=container)
    window.show()

    return application.exec()
