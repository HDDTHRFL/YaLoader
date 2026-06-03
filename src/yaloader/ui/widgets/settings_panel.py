from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class SettingsPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.downloads_dir_label = QLabel(self)
        self.choose_downloads_dir_button = QPushButton("Выбрать папку", self)

        self._configure_widgets()
        self._build_layout()

    def set_downloads_dir(self, *, downloads_dir: Path) -> None:
        text = f"Папка загрузок: {downloads_dir}"
        self.downloads_dir_label.setText(text)
        self.downloads_dir_label.setToolTip(str(downloads_dir))

    def _configure_widgets(self) -> None:
        self.setObjectName("PanelFrame")
        self.downloads_dir_label.setObjectName("MutedLabel")
        self.choose_downloads_dir_button.setObjectName("SecondaryButton")

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(10)

        downloads_layout = QHBoxLayout()
        downloads_layout.setContentsMargins(0, 0, 0, 0)
        downloads_layout.setSpacing(12)
        downloads_layout.addWidget(self.downloads_dir_label, stretch=1)
        downloads_layout.addWidget(self.choose_downloads_dir_button)

        root_layout.addLayout(downloads_layout)
