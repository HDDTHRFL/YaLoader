from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import override

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

DownloadsDirClickedCallback = Callable[[], None]


class ClickableDownloadsDirLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._clicked_callback: DownloadsDirClickedCallback | None = None

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    def set_clicked_callback(self, callback: DownloadsDirClickedCallback) -> None:
        self._clicked_callback = callback

    @override
    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            super().mouseReleaseEvent(event)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        if self._clicked_callback is not None:
            self._clicked_callback()

        event.accept()


class SettingsPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.downloads_dir_label = ClickableDownloadsDirLabel(self)
        self.choose_downloads_dir_button = QPushButton("Выбрать папку", self)

        self._configure_widgets()
        self._build_layout()

    def set_downloads_dir(self, *, downloads_dir: Path) -> None:
        text = f"Папка загрузок: {downloads_dir}"
        self.downloads_dir_label.setText(text)
        self.downloads_dir_label.setToolTip(f"Открыть папку загрузок: {downloads_dir}")

    def set_downloads_dir_clicked_callback(
        self,
        callback: DownloadsDirClickedCallback,
    ) -> None:
        self.downloads_dir_label.set_clicked_callback(callback)

    def _configure_widgets(self) -> None:
        self.setObjectName("PanelFrame")
        self.downloads_dir_label.setObjectName("DownloadsDirClickableLabel")
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
