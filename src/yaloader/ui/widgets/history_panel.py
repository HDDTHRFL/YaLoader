from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import override

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.domain.enums import DownloadStatus

HISTORY_PANEL_WIDTH = 380

SUPPORTED_EXTERNAL_URL_SCHEMES = frozenset({"http", "https"})

STATUS_TEXT = {
    DownloadStatus.COMPLETED: "Готово",
    DownloadStatus.FAILED: "Ошибка",
    DownloadStatus.CANCELED: "Отменено",
    DownloadStatus.PENDING: "Ожидает",
    DownloadStatus.RUNNING: "Выполняется",
}


class HistoryPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.refresh_button = QPushButton("Обновить", self)
        self.clear_button = QPushButton("Очистить", self)

        self._records_container = QWidget(self)
        self._records_layout = QVBoxLayout(self._records_container)
        self._scroll_area = QScrollArea(self)

        self._configure_widgets()
        self._build_layout()

    def set_records(self, records: Sequence[DownloadHistoryRecord]) -> None:
        self._clear_records_layout()

        if not records:
            empty_label = QLabel("История пока пустая", self._records_container)
            empty_label.setObjectName("MutedLabel")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._records_layout.addWidget(empty_label)
            self._records_layout.addStretch(1)
            return

        for record in records:
            self._records_layout.addWidget(HistoryRecordCard(record=record, parent=self))

        self._records_layout.addStretch(1)

    def _configure_widgets(self) -> None:
        self.setObjectName("HistoryPanel")
        self.setFixedWidth(HISTORY_PANEL_WIDTH)

        self.refresh_button.setObjectName("TinyGhostButton")
        self.clear_button.setObjectName("TinyDangerButton")

        self.refresh_button.setToolTip("Перечитать историю из файла")
        self.clear_button.setToolTip("Очистить историю загрузок")

        self._scroll_area.setObjectName("HistoryScrollArea")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setWidget(self._records_container)

        self._records_layout.setContentsMargins(0, 0, 0, 0)
        self._records_layout.setSpacing(10)

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 18, 16, 18)
        root_layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title_label = QLabel("История", self)
        title_label.setObjectName("SectionTitleLabel")

        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.refresh_button)
        header_layout.addWidget(self.clear_button)

        root_layout.addLayout(header_layout)
        root_layout.addWidget(self._scroll_area, stretch=1)

    def _clear_records_layout(self) -> None:
        while self._records_layout.count() > 0:
            layout_item = self._records_layout.takeAt(0)

            if layout_item is None:
                continue

            widget = layout_item.widget()

            if widget is not None:
                widget.deleteLater()


class HistoryRecordCard(QFrame):
    def __init__(
        self,
        *,
        record: DownloadHistoryRecord,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._record = record

        self._configure_widgets()
        self._build_layout()

    def _configure_widgets(self) -> None:
        self.setObjectName("HistoryCard")
        self.setProperty("state", self._record.status.value)
        self.setToolTip(self._record.url)

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        status_label = QLabel(STATUS_TEXT[self._record.status], self)
        status_label.setObjectName("HistoryStatusLabel")
        status_label.setProperty("state", self._record.status.value)

        time_label = QLabel(format_history_datetime(self._record.finished_at), self)
        time_label.setObjectName("HistoryTimeLabel")
        time_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        header_layout.addWidget(status_label)
        header_layout.addStretch(1)
        header_layout.addWidget(time_label)

        url_label = ClickableUrlLabel(url=self._record.url, parent=self)

        meta_label = QLabel(
            (
                f"{self._record.mode.value} · "
                f"{self._record.output_format.value} · "
                f"{self._record.video_quality.value}"
            ),
            self,
        )
        meta_label.setObjectName("MutedLabel")

        folder_label = ClickableDirectoryLabel(
            directory_path=self._record.target_dir,
            parent=self,
        )

        layout.addLayout(header_layout)
        layout.addWidget(url_label)
        layout.addWidget(meta_label)
        layout.addWidget(folder_label)

        if self._record.error_message:
            error_label = QLabel(self._record.error_message, self)
            error_label.setObjectName("HistoryErrorLabel")
            error_label.setWordWrap(True)
            error_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(error_label)


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


def format_history_datetime(value: datetime) -> str:
    return value.astimezone().strftime("%d.%m.%Y %H:%M")
