from __future__ import annotations

from collections.abc import Callable
from typing import override

from PyQt6.QtCore import QEvent, QObject, QPoint, QSize, Qt
from PyQt6.QtGui import QClipboard, QContextMenuEvent, QGuiApplication
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.domain.source_platform import detect_source_platform
from yaloader.ui.platform_icons import build_source_platform_icon
from yaloader.ui.widgets.common.context_menu_actions import (
    add_menu_action,
    add_menu_button_action,
    create_context_menu,
)
from yaloader.ui.widgets.history.formatting import (
    STATUS_TEXT,
    format_history_datetime,
    format_history_quality,
    format_history_title,
)
from yaloader.ui.widgets.history.labels import ClickablePathLabel, ClickableUrlLabel

HISTORY_PLATFORM_ICON_SIZE = 18
HISTORY_META_ICON_SPACING = 6


class HistoryRecordCard(QFrame):
    def __init__(
        self,
        *,
        record: DownloadHistoryRecord,
        on_add_to_queue: Callable[[DownloadHistoryRecord], None] | None,
        on_delete_record: Callable[[DownloadHistoryRecord], None] | None,
        on_copy_url: Callable[[DownloadHistoryRecord], None] | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._record = record
        self._on_add_to_queue = on_add_to_queue
        self._on_delete_record = on_delete_record
        self._on_copy_url = on_copy_url

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
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

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
        meta_row = self._build_meta_row()

        output_path = self._record.output_path or self._record.target_dir
        path_label = ClickablePathLabel(
            path=output_path,
            parent=self,
        )

        self._configure_compressible_label(url_label)
        self._configure_compressible_container(meta_row)
        self._configure_compressible_label(path_label)

        self._install_context_menu_filter(status_label)
        self._install_context_menu_filter(time_label)
        self._install_context_menu_filter(url_label)
        self._install_context_menu_filter(meta_row)
        self._install_context_menu_filter(path_label)

        if title_label is not None:
            self._configure_compressible_label(title_label)
            self._install_context_menu_filter(title_label)

        layout.addLayout(header_layout)

        if title_label is not None:
            layout.addWidget(title_label)

        layout.addWidget(url_label)
        layout.addWidget(meta_row)
        layout.addWidget(path_label)

        if self._record.error_message:
            error_label = QLabel(self._record.error_message, self)
            error_label.setObjectName("HistoryErrorLabel")
            error_label.setWordWrap(True)
            error_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._configure_compressible_label(error_label)
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

    def _build_meta_row(self) -> QWidget:
        meta_row = QWidget(self)
        meta_row.setObjectName("HistoryMetaRow")

        meta_layout = QHBoxLayout(meta_row)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(HISTORY_META_ICON_SPACING)

        platform_icon_label = self._build_platform_icon_label()
        meta_label = QLabel(
            (
                f"{self._record.mode.value} · "
                f"{self._record.output_format.value} · "
                f"{format_history_quality(record=self._record)}"
            ),
            meta_row,
        )
        meta_label.setObjectName("MutedLabel")
        self._configure_compressible_label(meta_label)
        self._install_context_menu_filter(meta_label)

        if platform_icon_label is not None:
            self._install_context_menu_filter(platform_icon_label)
            meta_layout.addWidget(
                platform_icon_label,
                0,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            )

        meta_layout.addWidget(meta_label, 1)

        return meta_row

    def _build_platform_icon_label(self) -> QLabel | None:
        platform = detect_source_platform(url=self._record.url)
        platform_icon = build_source_platform_icon(platform=platform)

        if platform_icon.isNull():
            return None

        platform_icon_label = QLabel(self)
        platform_icon_label.setObjectName("HistoryPlatformIconLabel")
        platform_icon_label.setFixedSize(QSize(HISTORY_PLATFORM_ICON_SIZE, HISTORY_PLATFORM_ICON_SIZE))
        platform_icon_label.setPixmap(
            platform_icon.pixmap(QSize(HISTORY_PLATFORM_ICON_SIZE, HISTORY_PLATFORM_ICON_SIZE))
        )
        platform_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        return platform_icon_label

    def _configure_compressible_label(self, label: QLabel) -> None:
        label.setMinimumWidth(0)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def _configure_compressible_container(self, widget: QWidget) -> None:
        widget.setMinimumWidth(0)
        widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def _install_context_menu_filter(self, widget: QWidget) -> None:
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        widget.installEventFilter(self)

    def _show_context_menu(self, *, global_position: QPoint) -> None:
        context_menu = create_context_menu(parent=self)

        copy_link_action = add_menu_action(
            menu=context_menu,
            text="Скопировать ссылку",
        )

        add_to_queue_action = add_menu_action(
            menu=context_menu,
            text="Добавить в очередь загрузок",
        )
        add_to_queue_action.setEnabled(self._on_add_to_queue is not None)

        delete_record_action = add_menu_button_action(
            menu=context_menu,
            text="Удалить из истории",
            object_name="MenuDangerButton",
        )
        delete_record_action.setEnabled(self._on_delete_record is not None)

        selected_action = context_menu.exec(global_position)

        if selected_action is None:
            return

        if selected_action == copy_link_action:
            self._copy_url_to_clipboard()
            return

        if selected_action == add_to_queue_action and self._on_add_to_queue is not None:
            self._on_add_to_queue(self._record)
            return

        if selected_action == delete_record_action and self._on_delete_record is not None:
            self._on_delete_record(self._record)

    def _copy_url_to_clipboard(self) -> None:
        clipboard = QGuiApplication.clipboard()

        if not isinstance(clipboard, QClipboard):
            return

        clipboard.setText(self._record.url)

        if self._on_copy_url is not None:
            self._on_copy_url(self._record)
