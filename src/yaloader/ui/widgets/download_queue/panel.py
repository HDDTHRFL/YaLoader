from __future__ import annotations

from typing import Final

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from yaloader.ui.widgets.download_queue.columns import QUEUE_ROW_HEIGHT
from yaloader.ui.widgets.download_queue.table import DownloadQueueTable

REMOVE_SELECTED_QUEUE_ITEMS_TOOLTIP: Final = "Delete"
CLEAR_DOWNLOAD_QUEUE_TOOLTIP: Final = "Shift + Delete"

QUEUE_MINIMUM_VISIBLE_ROWS_NUMERATOR = 3
QUEUE_MINIMUM_VISIBLE_ROWS_DENOMINATOR = 2
QUEUE_TABLE_HEADER_AND_FRAME_HEIGHT = 44
QUEUE_TABLE_MINIMUM_HEIGHT = (
    QUEUE_ROW_HEIGHT * QUEUE_MINIMUM_VISIBLE_ROWS_NUMERATOR // QUEUE_MINIMUM_VISIBLE_ROWS_DENOMINATOR
    + QUEUE_TABLE_HEADER_AND_FRAME_HEIGHT
)

QUEUE_PANEL_VERTICAL_MARGINS = 36
QUEUE_PANEL_VERTICAL_SPACING = 24
QUEUE_PANEL_TITLE_HEIGHT = 24
QUEUE_PANEL_ACTIONS_HEIGHT = 38
QUEUE_PANEL_HEIGHT_SAFETY_MARGIN = 8
QUEUE_PANEL_MINIMUM_HEIGHT = (
    QUEUE_TABLE_MINIMUM_HEIGHT
    + QUEUE_PANEL_VERTICAL_MARGINS
    + QUEUE_PANEL_VERTICAL_SPACING
    + QUEUE_PANEL_TITLE_HEIGHT
    + QUEUE_PANEL_ACTIONS_HEIGHT
    + QUEUE_PANEL_HEIGHT_SAFETY_MARGIN
)


class DownloadQueuePanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.queue_table = DownloadQueueTable(self)
        self.start_queue_button = QPushButton("Скачать очередь", self)
        self.remove_from_queue_button = QPushButton("Удалить выбранное", self)
        self.clear_queue_button = QPushButton("Очистить очередь", self)

        self._configure_widgets()
        self._build_layout()

    def _configure_widgets(self) -> None:
        self.setObjectName("PanelFrame")
        self.setMinimumHeight(QUEUE_PANEL_MINIMUM_HEIGHT)
        self.queue_table.setMinimumHeight(QUEUE_TABLE_MINIMUM_HEIGHT)

        self.start_queue_button.setObjectName("SuccessButton")
        self.remove_from_queue_button.setObjectName("SecondaryButton")
        self.clear_queue_button.setObjectName("SecondaryButton")

        self.remove_from_queue_button.setToolTip(REMOVE_SELECTED_QUEUE_ITEMS_TOOLTIP)
        self.clear_queue_button.setToolTip(CLEAR_DOWNLOAD_QUEUE_TOOLTIP)

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel("Очередь загрузок", self)
        title_label.setObjectName("SectionTitleLabel")

        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(12)
        actions_layout.addWidget(self.remove_from_queue_button)
        actions_layout.addWidget(self.clear_queue_button)
        actions_layout.addStretch(1)
        actions_layout.addWidget(self.start_queue_button)

        layout.addWidget(title_label)
        layout.addWidget(self.queue_table, stretch=1)
        layout.addLayout(actions_layout)
