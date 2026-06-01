from __future__ import annotations

from collections.abc import Callable
from typing import override

from PyQt6.QtCore import QEvent, QObject, QPoint, Qt
from PyQt6.QtGui import QAction, QContextMenuEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.ui.widgets.context_menu_actions import (
    add_menu_button_action,
    create_context_menu,
)
from yaloader.ui.widgets.history_formatting import (
    STATUS_TEXT,
    format_history_datetime,
    format_history_quality,
    format_history_title,
)
from yaloader.ui.widgets.history_labels import ClickableDirectoryLabel, ClickableUrlLabel


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

        title_label = self._build_title_label()
        url_label = ClickableUrlLabel(url=self._record.url, parent=self)

        meta_label = QLabel(
            (
                f"{self._record.mode.value} · "
                f"{self._record.output_format.value} · "
                f"{format_history_quality(record=self._record)}"
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

        if title_label is not None:
            self._install_context_menu_filter(title_label)

        layout.addLayout(header_layout)

        if title_label is not None:
            layout.addWidget(title_label)

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

    def _build_title_label(self) -> QLabel | None:
        title = format_history_title(record=self._record)

        if title is None:
            return None

        title_label = QLabel(title, self)
        title_label.setObjectName("HistoryTitleLabel")
        title_label.setWordWrap(True)
        title_label.setToolTip(title)
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        return title_label

    def _install_context_menu_filter(self, widget: QWidget) -> None:
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        widget.installEventFilter(self)

    def _show_context_menu(self, *, global_position: QPoint) -> None:
        context_menu = create_context_menu(parent=self)

        add_to_queue_action = QAction("Добавить в очередь загрузок", context_menu)
        add_to_queue_action.setEnabled(self._on_add_to_queue is not None)
        context_menu.addAction(add_to_queue_action)

        delete_record_action = add_menu_button_action(
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
