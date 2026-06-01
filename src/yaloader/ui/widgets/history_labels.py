from __future__ import annotations

from pathlib import Path
from typing import override

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QMouseEvent
from PyQt6.QtWidgets import QLabel, QWidget

SUPPORTED_EXTERNAL_URL_SCHEMES = frozenset({"http", "https"})


class ClickableUrlLabel(QLabel):
    def __init__(
        self,
        *,
        url: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(url, parent)

        self._url = url

        self.setObjectName("HistoryUrlLabel")
        self.setWordWrap(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Открыть ссылку в браузере: {url}")

    @override
    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            super().mouseReleaseEvent(event)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        external_url = QUrl(self._url)

        if self._is_supported_external_url(external_url=external_url):
            QDesktopServices.openUrl(external_url)

        event.accept()

    def _is_supported_external_url(self, *, external_url: QUrl) -> bool:
        scheme = external_url.scheme().casefold()
        return external_url.isValid() and scheme in SUPPORTED_EXTERNAL_URL_SCHEMES


class ClickableDirectoryLabel(QLabel):
    def __init__(
        self,
        *,
        directory_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(str(directory_path), parent)

        self._directory_path = directory_path

        self.setObjectName("HistoryPathLabel")
        self.setWordWrap(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Открыть папку: {directory_path}")

    @override
    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            super().mouseReleaseEvent(event)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        if self._directory_path.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._directory_path)))

        event.accept()
