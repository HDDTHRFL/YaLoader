from __future__ import annotations

from pathlib import Path
from typing import override

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QMouseEvent
from PyQt6.QtWidgets import QLabel, QWidget

from yaloader.infrastructure.windows.explorer import reveal_path_in_file_manager

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


class ClickablePathLabel(QLabel):
    def __init__(
        self,
        *,
        path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(str(path), parent)

        self._path = path

        self.setObjectName("HistoryPathLabel")
        self.setWordWrap(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Открыть расположение: {path}")

    @override
    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            super().mouseReleaseEvent(event)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        if not reveal_path_in_file_manager(path=self._path):
            self._open_fallback_location()

        event.accept()

    def _open_fallback_location(self) -> None:
        existing_path = self._resolve_existing_path()

        if existing_path is None:
            return

        if existing_path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(existing_path.parent.resolve())))
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(existing_path.resolve())))

    def _resolve_existing_path(self) -> Path | None:
        if self._path.exists():
            return self._path

        parent_path = self._path.parent

        if parent_path.exists():
            return parent_path

        return None
