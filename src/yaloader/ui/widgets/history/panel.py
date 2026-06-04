from __future__ import annotations

from collections.abc import Callable, Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QScroller,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.ui.widgets.common.overlay_scrollbar import OverlayVerticalScrollBarController
from yaloader.ui.widgets.history.record_card import HistoryRecordCard

HISTORY_PANEL_WIDTH = 380


class HistoryPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.refresh_button = QPushButton("Обновить", self)
        self.clear_button = QPushButton("Очистить", self)

        self._records_container = QWidget(self)
        self._records_layout = QVBoxLayout(self._records_container)
        self._scroll_area = QScrollArea(self)
        self._overlay_scroll_bar_controller: OverlayVerticalScrollBarController | None = None

        self._records_count = 0
        self._on_add_to_queue: Callable[[DownloadHistoryRecord], None] | None = None
        self._on_delete_record: Callable[[DownloadHistoryRecord], None] | None = None
        self._on_copy_url: Callable[[DownloadHistoryRecord], None] | None = None

        self._configure_widgets()
        self._build_layout()

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
            return

        for record in records:
            self._records_layout.addWidget(
                HistoryRecordCard(
                    record=record,
                    on_add_to_queue=self._on_add_to_queue,
                    on_delete_record=self._on_delete_record,
                    on_copy_url=self._on_copy_url,
                    parent=self,
                )
            )

        self._records_layout.addStretch(1)

    def has_records(self) -> bool:
        return self._records_count > 0

    def set_drawer_width(self, *, width: int) -> None:
        normalized_width = max(0, min(HISTORY_PANEL_WIDTH, width))
        self.setMinimumWidth(normalized_width)
        self.setMaximumWidth(normalized_width)
        self.resize(normalized_width, self.height())

    def current_drawer_width(self) -> int:
        return self.width()

    def _configure_widgets(self) -> None:
        self.setObjectName("HistoryPanel")
        self.set_drawer_width(width=HISTORY_PANEL_WIDTH)

        self.refresh_button.setObjectName("TinyGhostButton")
        self.clear_button.setObjectName("TinyDangerButton")

        self.refresh_button.setToolTip("Перечитать историю из файла")
        self.clear_button.setToolTip("Очистить историю загрузок")

        self._scroll_area.setObjectName("HistoryScrollArea")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setWidget(self._records_container)

        self._overlay_scroll_bar_controller = OverlayVerticalScrollBarController(
            scroll_area=self._scroll_area,
        )

        QScroller.grabGesture(
            self._scroll_area.viewport(),
            QScroller.ScrollerGestureType.LeftMouseButtonGesture,
        )

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
