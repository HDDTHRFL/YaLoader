from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import cast, override

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QScrollBar,
    QScroller,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.ui.widgets.common.overlay_scrollbar import OverlayVerticalScrollBarController
from yaloader.ui.widgets.history.record_card import HistoryRecordCard

HISTORY_PANEL_WIDTH = 380
HISTORY_PANEL_HORIZONTAL_MARGIN = 16
HISTORY_RECORDS_CONTAINER_MIN_WIDTH = HISTORY_PANEL_WIDTH - HISTORY_PANEL_HORIZONTAL_MARGIN * 2


class HistoryPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._content_widget = QWidget(self)

        self.refresh_button = QPushButton("Обновить", self._content_widget)
        self.clear_button = QPushButton("Очистить", self._content_widget)

        self._records_container = QWidget(self._content_widget)
        self._records_layout = QVBoxLayout(self._records_container)
        self._scroll_area = QScrollArea(self._content_widget)
        self._overlay_scroll_bar_controller: OverlayVerticalScrollBarController | None = None

        self._records_count = 0
        self._on_add_to_queue: Callable[[DownloadHistoryRecord], None] | None = None
        self._on_delete_record: Callable[[DownloadHistoryRecord], None] | None = None
        self._on_copy_url: Callable[[DownloadHistoryRecord], None] | None = None

        self._configure_widgets()
        self._build_layout()
        self._sync_content_geometry()

    @override
    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._sync_content_geometry()
        self._sync_records_container_later()

    @override
    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if (
            event is not None
            and watched
            in {
                self._scroll_area,
                self._viewport(),
                self._records_container,
            }
            and event.type()
            in {
                QEvent.Type.Resize,
                QEvent.Type.Show,
                QEvent.Type.LayoutRequest,
                QEvent.Type.MouseMove,
                QEvent.Type.Wheel,
            }
        ):
            self._sync_records_container_width()
            self._lock_horizontal_scroll_position()
            QTimer.singleShot(0, self._lock_horizontal_scroll_position)

        return super().eventFilter(watched, event)

    def set_context_menu_callbacks(
        self,
        *,
        on_add_to_queue: Callable[[DownloadHistoryRecord], None],
        on_delete_record: Callable[[DownloadHistoryRecord], None],
        on_copy_url: Callable[[DownloadHistoryRecord], None] | None = None,
    ) -> None:
        self._on_add_to_queue = on_add_to_queue
        self._on_delete_record = on_delete_record
        self._on_copy_url = on_copy_url

    def set_records(self, records: Sequence[DownloadHistoryRecord]) -> None:
        self._clear_records_layout()
        self._records_count = len(records)

        if not records:
            empty_label = QLabel("История пока пустая", self._records_container)
            empty_label.setObjectName("MutedLabel")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._records_layout.addWidget(empty_label)
            self._records_layout.addStretch(1)
            self._sync_records_container_later()
            return

        for record in records:
            self._records_layout.addWidget(
                HistoryRecordCard(
                    record=record,
                    on_add_to_queue=self._on_add_to_queue,
                    on_delete_record=self._on_delete_record,
                    on_copy_url=self._on_copy_url,
                    parent=self._records_container,
                )
            )

        self._records_layout.addStretch(1)
        self._sync_records_container_later()

    def has_records(self) -> bool:
        return self._records_count > 0

    def set_drawer_width(self, *, width: int) -> None:
        normalized_width = max(0, min(HISTORY_PANEL_WIDTH, width))
        self.setFixedWidth(normalized_width)
        self._sync_content_geometry()
        self.updateGeometry()
        self.update()

    def current_drawer_width(self) -> int:
        return max(0, min(HISTORY_PANEL_WIDTH, self.width()))

    def _configure_widgets(self) -> None:
        self.setObjectName("HistoryPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.set_drawer_width(width=HISTORY_PANEL_WIDTH)

        self._content_widget.setObjectName("HistoryPanelContent")
        self._content_widget.setFixedWidth(HISTORY_PANEL_WIDTH)
        self._content_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.refresh_button.setObjectName("TinyGhostButton")
        self.clear_button.setObjectName("TinyDangerButton")

        self.refresh_button.setToolTip("Перечитать историю из файла")
        self.clear_button.setToolTip("Очистить историю загрузок")

        self._records_container.setObjectName("HistoryRecordsContainer")
        self._records_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._scroll_area.setObjectName("HistoryScrollArea")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setWidget(self._records_container)
        self._viewport().setObjectName("HistoryScrollAreaViewport")
        self._viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        horizontal_scroll_bar = self._horizontal_scroll_bar()
        horizontal_scroll_bar.setEnabled(False)
        horizontal_scroll_bar.rangeChanged.connect(self._handle_horizontal_scroll_range_changed)
        horizontal_scroll_bar.valueChanged.connect(self._handle_horizontal_scroll_value_changed)

        self._scroll_area.installEventFilter(self)
        self._viewport().installEventFilter(self)
        self._records_container.installEventFilter(self)

        self._overlay_scroll_bar_controller = OverlayVerticalScrollBarController(
            scroll_area=self._scroll_area,
        )

        QScroller.grabGesture(
            self._viewport(),
            QScroller.ScrollerGestureType.LeftMouseButtonGesture,
        )

        self._records_layout.setContentsMargins(0, 0, 0, 0)
        self._records_layout.setSpacing(10)

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self._content_widget)
        root_layout.setContentsMargins(
            HISTORY_PANEL_HORIZONTAL_MARGIN,
            18,
            HISTORY_PANEL_HORIZONTAL_MARGIN,
            18,
        )
        root_layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title_label = QLabel("История", self._content_widget)
        title_label.setObjectName("SectionTitleLabel")

        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.refresh_button)
        header_layout.addWidget(self.clear_button)

        root_layout.addLayout(header_layout)
        root_layout.addWidget(self._scroll_area, stretch=1)

    def _sync_content_geometry(self) -> None:
        self._content_widget.setGeometry(
            0,
            0,
            HISTORY_PANEL_WIDTH,
            max(0, self.height()),
        )

    def _sync_records_container_later(self) -> None:
        self._sync_records_container_width()
        self._lock_horizontal_scroll_position()
        QTimer.singleShot(0, self._sync_records_container_width)
        QTimer.singleShot(0, self._lock_horizontal_scroll_position)

    def _sync_records_container_width(self) -> None:
        viewport_width = self._viewport().width()
        target_width = max(HISTORY_RECORDS_CONTAINER_MIN_WIDTH, viewport_width)

        self._records_container.setMinimumWidth(target_width)
        self._records_container.setMaximumWidth(target_width)

    def _handle_horizontal_scroll_range_changed(self, _minimum: int, _maximum: int) -> None:
        self._lock_horizontal_scroll_position()

    def _handle_horizontal_scroll_value_changed(self, _value: int) -> None:
        self._lock_horizontal_scroll_position()

    def _lock_horizontal_scroll_position(self) -> None:
        horizontal_scroll_bar = self._horizontal_scroll_bar()

        if horizontal_scroll_bar.value() == 0:
            return

        horizontal_scroll_bar.setValue(0)

    def _viewport(self) -> QWidget:
        return cast(QWidget, self._scroll_area.viewport())

    def _horizontal_scroll_bar(self) -> QScrollBar:
        return cast(QScrollBar, self._scroll_area.horizontalScrollBar())

    def _clear_records_layout(self) -> None:
        while self._records_layout.count() > 0:
            layout_item = self._records_layout.takeAt(0)

            if layout_item is None:
                continue

            widget = layout_item.widget()

            if widget is not None:
                widget.deleteLater()
