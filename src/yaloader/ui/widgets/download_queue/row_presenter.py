from __future__ import annotations

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem

from yaloader.ui.widgets.download_queue.columns import (
    FILE_COLUMN_INDEX,
    FOLDER_COLUMN_INDEX,
    MODE_COLUMN_INDEX,
    QUALITY_COLUMN_INDEX,
    STATUS_PROGRESS_COLUMN_INDEX,
    URL_COLUMN_INDEX,
)
from yaloader.ui.widgets.download_queue.quality_presenter import DownloadQueueQualityPresenter
from yaloader.ui.widgets.download_queue.row_cell_text import (
    build_file_cell_text,
    build_mode_cell_text,
    build_quality_cell_text,
)
from yaloader.ui.widgets.download_queue.row_state import QueueTableRowState
from yaloader.ui.widgets.download_queue.url_presenter import DownloadQueueUrlPresenter


class DownloadQueueRowPresenter:
    def __init__(
        self,
        *,
        table: QTableWidget,
        quality_presenter: DownloadQueueQualityPresenter,
        url_presenter: DownloadQueueUrlPresenter,
    ) -> None:
        self._table = table
        self._quality_presenter = quality_presenter
        self._url_presenter = url_presenter

    def set_task_row_values(self, *, row_index: int, row_state: QueueTableRowState) -> None:
        task = row_state.task
        is_metadata_pending = row_state.is_metadata_resolution_pending
        values_by_column = {
            MODE_COLUMN_INDEX: build_mode_cell_text(task=task),
            URL_COLUMN_INDEX: task.url.value,
            QUALITY_COLUMN_INDEX: build_quality_cell_text(
                task=task,
                is_metadata_pending=is_metadata_pending,
            ),
            FILE_COLUMN_INDEX: build_file_cell_text(
                task=task,
                is_metadata_pending=is_metadata_pending,
            ),
            STATUS_PROGRESS_COLUMN_INDEX: task.status.value,
            FOLDER_COLUMN_INDEX: str(task.target_dir),
        }

        for column_index, value in values_by_column.items():
            table_item = self._table.item(row_index, column_index)

            if table_item is None:
                table_item = QTableWidgetItem(value)
                self._table.setItem(row_index, column_index, table_item)
            else:
                table_item.setText(value)

            if column_index == URL_COLUMN_INDEX:
                self._url_presenter.configure_url_item(
                    row_index=row_index,
                    table_item=table_item,
                    task=task,
                )
                continue

            if column_index == QUALITY_COLUMN_INDEX:
                table_item.setToolTip(self._quality_presenter.build_cell_tooltip(task=task))
            else:
                table_item.setToolTip(value)
