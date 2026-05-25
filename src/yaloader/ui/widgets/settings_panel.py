from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class SettingsPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.downloads_dir_label = QLabel(self)
        self.cookies_status_label = QLabel(self)
        self.choose_downloads_dir_button = QPushButton("Выбрать папку", self)
        self.delete_cookies_button = QPushButton("Удалить cookies.txt", self)

        self._configure_widgets()
        self._build_layout()

    def set_downloads_dir(self, downloads_dir: Path) -> None:
        self.downloads_dir_label.setText(f"Папка загрузок: {downloads_dir}")
        self.downloads_dir_label.setToolTip(str(downloads_dir))

    def set_cookies_status(self, *, cookies_file: Path) -> None:
        if cookies_file.is_file():
            file_size = cookies_file.stat().st_size
            self.cookies_status_label.setText(f"cookies.txt: найден ({file_size} байт)")
        else:
            self.cookies_status_label.setText("cookies.txt: не найден")

        self.cookies_status_label.setToolTip(str(cookies_file))
        self.delete_cookies_button.setToolTip(str(cookies_file))

    def _configure_widgets(self) -> None:
        self.setObjectName("PanelFrame")

        self.downloads_dir_label.setObjectName("MutedLabel")
        self.downloads_dir_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.cookies_status_label.setObjectName("MutedLabel")
        self.cookies_status_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

    def _build_layout(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        labels_layout = QVBoxLayout()
        labels_layout.setContentsMargins(0, 0, 0, 0)
        labels_layout.setSpacing(4)
        labels_layout.addWidget(self.downloads_dir_label)
        labels_layout.addWidget(self.cookies_status_label)

        layout.addLayout(labels_layout, stretch=1)
        layout.addWidget(self.choose_downloads_dir_button)
        layout.addWidget(self.delete_cookies_button)
