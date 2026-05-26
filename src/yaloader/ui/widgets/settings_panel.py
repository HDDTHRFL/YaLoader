from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget


class SettingsPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.downloads_dir_label = QLabel(self)
        self.choose_downloads_dir_button = QPushButton("Выбрать папку", self)
        self.delete_cookies_button = QPushButton("Удалить cookies.txt", self)

        self._configure_widgets()
        self._build_layout()

    def set_downloads_dir(self, downloads_dir: Path) -> None:
        self.downloads_dir_label.setText(f"Папка загрузок: {downloads_dir}")
        self.downloads_dir_label.setToolTip(str(downloads_dir))

    def set_cookies_file_path(self, cookies_file: Path) -> None:
        self.delete_cookies_button.setToolTip(str(cookies_file))

    def _configure_widgets(self) -> None:
        self.setObjectName("PanelFrame")

        self.downloads_dir_label.setObjectName("MutedLabel")
        self.downloads_dir_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.choose_downloads_dir_button.setObjectName("SecondaryButton")
        self.delete_cookies_button.setObjectName("DangerGhostButton")

    def _build_layout(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        layout.addWidget(self.downloads_dir_label, stretch=1)
        layout.addWidget(self.choose_downloads_dir_button)
        layout.addWidget(self.delete_cookies_button)
