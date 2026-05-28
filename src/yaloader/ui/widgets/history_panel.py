from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import override

from PyQt6.QtCore import QEvent, QObject, QPoint, Qt, QUrl
from PyQt6.QtGui import QAction, QContextMenuEvent, QDesktopServices, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.domain.enums import DownloadStatus

HISTORY_PANEL_WIDTH = 380

SUPPORTED_EXTERNAL_URL_SCHEMES = frozenset({"http", "https"})

HISTORY_CONTEXT_MENU_STYLESHEET = """
QMenu {
    background-color: #161B22;
    color: #F0F3F6;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #1F6FEB;
    color: #FFFFFF;
}

QPushButton#MenuDangerButton {
    min-height: 32px;
    padding: 0 24px;
    background-color: transparent;
    color: #FCA5A5;
    border: none;
    border-radius: 6px;
    font-weight: 500;
    text-align: left;
}

QPushButton#MenuDangerButton:hover {
    background-color: #3A1518;
    color: #FECACA;
}

QPushButton#MenuDangerButton:disabled {
    background-color: transparent;
    color: #5F6875;
    border: none;
}

QPushButton#MenuDangerButton:disabled:hover {
    background-color: transparent;
    color: #5F6875;
}
"""

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

        self._on_add_to_queue: Callable[[DownloadHistoryRecord], None] | None = None
        self._on_delete_record: Callable[[DownloadHistoryRecord], None] | None = None

        self._configure_widgets()
        self._build_layout()

    def set_context_menu_callbacks(
        self,
        *,
        on_add_to_queue: Callable[[DownloadHistoryRecord], None],
        on_delete_record: Callable[[DownloadHistoryRecord], None],
    ) -> None:
        self._on_add_to_queue = on_add_to_queue
        self._on_delete_record = on_delete_record

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
            self._records_layout.addWidget(
                HistoryRecordCard(
                    record=record,
                    on_add_to_queue=self._on_add_to_queue,
                    on_delete_record=self._on_delete_record,
                    parent=self,
                )
            )

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
        on_add_to_queue: Callable[[DownloadHistoryRecord], None] | None,
        on_delete_record: Callable[[DownloadHistoryRecord], None] | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._record = record
        self._on_add_to_queue = on_add_to_queue
        self._on_delete_record = on_delete_record

        self._configure_widgets()
        self._build_layout()

    @override
    def contextMenuEvent(self, event: QContextMenuEvent | None) -> None:
        if event is None:
            return

        self._show_context_menu(global_position=event.globalPos())
        event.accept()

    @override
    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if event is None:
            return super().eventFilter(watched, event)

        if event.type() == QEvent.Type.ContextMenu and isinstance(event, QContextMenuEvent):
            self._show_context_menu(global_position=event.globalPos())
            event.accept()
            return True

        return super().eventFilter(watched, event)

    def _configure_widgets(self) -> None:
        self.setObjectName("HistoryCard")
        self.setProperty("state", self._record.status.value)
        self.setToolTip(self._record.url)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)

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

        self._install_context_menu_filter(status_label)
        self._install_context_menu_filter(time_label)
        self._install_context_menu_filter(url_label)
        self._install_context_menu_filter(meta_label)
        self._install_context_menu_filter(folder_label)

        layout.addLayout(header_layout)
        layout.addWidget(url_label)
        layout.addWidget(meta_label)
        layout.addWidget(folder_label)

        if self._record.error_message:
            error_label = QLabel(self._record.error_message, self)
            error_label.setObjectName("HistoryErrorLabel")
            error_label.setWordWrap(True)
            error_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._install_context_menu_filter(error_label)
            layout.addWidget(error_label)

    def _install_context_menu_filter(self, widget: QWidget) -> None:
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        widget.installEventFilter(self)

    def _show_context_menu(self, *, global_position: QPoint) -> None:
        context_menu = QMenu(self)
        context_menu.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        context_menu.setStyleSheet(HISTORY_CONTEXT_MENU_STYLESHEET)

        add_to_queue_action = QAction("Добавить в очередь загрузок", context_menu)
        add_to_queue_action.setEnabled(self._on_add_to_queue is not None)
        context_menu.addAction(add_to_queue_action)

        delete_record_action = self._add_menu_button_action(
            menu=context_menu,
            text="Удалить из истории",
            object_name="MenuDangerButton",
        )
        delete_record_action.setEnabled(self._on_delete_record is not None)

        selected_action = context_menu.exec(global_position)

        if selected_action is None:
            return

        if selected_action == add_to_queue_action and self._on_add_to_queue is not None:
            self._on_add_to_queue(self._record)
            return

        if selected_action == delete_record_action and self._on_delete_record is not None:
            self._on_delete_record(self._record)

    def _add_menu_button_action(
        self,
        *,
        menu: QMenu,
        text: str,
        object_name: str,
    ) -> QWidgetAction:
        action = QWidgetAction(menu)
        button = QPushButton(text, menu)
        button.setObjectName(object_name)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        def handle_button_clicked(_checked: bool = False) -> None:
            action.trigger()
            menu.close()

        button.clicked.connect(handle_button_clicked)

        action.setDefaultWidget(button)
        menu.addAction(action)

        return action


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
