from __future__ import annotations

from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QWidget

from yaloader.ui.widgets.download_queue_columns import (
    QUEUE_COLUMN_COUNT,
    QUEUE_ROW_HEIGHT,
    TABLE_RIGHT_OVERDRAW_WIDTH,
    calculate_queue_column_widths,
)
from yaloader.ui.widgets.download_queue_delegate import DownloadQueueItemDelegate


def configure_download_queue_table(*, table: QTableWidget) -> None:
    table.setColumnCount(QUEUE_COLUMN_COUNT)
    table.setHorizontalHeaderLabels(
        [
            "Режим",
            "Ссылка",
            "Качество",
            "Формат",
            "Статус",
            "Прогресс",
            "Папка",
        ]
    )
    table.setItemDelegate(DownloadQueueItemDelegate(table))
    table.setAlternatingRowColors(True)
    table.setMouseTracking(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setWordWrap(False)

    horizontal_header = cast(QHeaderView, table.horizontalHeader())
    horizontal_header.setSectionsMovable(False)
    horizontal_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    horizontal_header.setStretchLastSection(False)

    vertical_header = cast(QHeaderView, table.verticalHeader())
    vertical_header.hide()
    vertical_header.setDefaultSectionSize(QUEUE_ROW_HEIGHT)
    vertical_header.setMinimumSectionSize(QUEUE_ROW_HEIGHT)
    vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

    resize_download_queue_table_columns_to_viewport(table=table)


def resize_download_queue_table_columns_to_viewport(*, table: QTableWidget) -> None:
    if table.columnCount() == 0:
        return

    viewport = cast(QWidget, table.viewport())
    available_width = viewport.width() + TABLE_RIGHT_OVERDRAW_WIDTH
    column_widths = calculate_queue_column_widths(available_width=available_width)

    for column_index, column_width in column_widths.items():
        table.setColumnWidth(column_index, column_width)
