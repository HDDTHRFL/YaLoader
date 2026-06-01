from __future__ import annotations

from uuid import UUID

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QProgressBar, QTableWidget, QTableWidgetItem

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus
from yaloader.ui.widgets.download_queue_columns import PROGRESS_COLUMN_INDEX

EMPTY_PROGRESS_TEXT = "—"


class DownloadQueueProgressPresenter:
    def __init__(
        self,
        *,
        table: QTableWidget,
        row_by_task_id: dict[UUID, int],
    ) -> None:
        self._table = table
        self._row_by_task_id = row_by_task_id

    def prepare_tasks_for_download(self, *, task_ids: tuple[UUID, ...]) -> None:
        for task_id in task_ids:
            row_index = self._row_by_task_id.get(task_id)

            if row_index is None:
                continue

            progress_bar = self._ensure_progress_bar(row_index=row_index)
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setFormat("0%")

    def set_task_progress(self, progress: DownloadProgress) -> None:
        row_index = self._row_by_task_id.get(progress.task_id)

        if row_index is None:
            return

        progress_bar = self._ensure_progress_bar(row_index=row_index)

        if progress.percent is None:
            progress_bar.setRange(0, 0)
            progress_bar.setFormat(progress.status_text)
            return

        progress_bar.setRange(0, 100)
        progress_bar.setValue(progress.progress_bar_value)
        progress_bar.setFormat(f"{progress.progress_bar_value}%")

    def sync_with_task_status(self, *, row_index: int, task: DownloadTask) -> None:
        if task.status is DownloadStatus.COMPLETED:
            progress_bar = self._ensure_progress_bar(row_index=row_index)
            progress_bar.setRange(0, 100)
            progress_bar.setValue(100)
            progress_bar.setFormat("100%")
            return

        if task.status is DownloadStatus.RUNNING:
            progress_bar = self._ensure_progress_bar(row_index=row_index)
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setFormat("0%")
            return

        if task.status is DownloadStatus.FAILED:
            self.set_text(row_index=row_index, text="Ошибка")
            return

        if task.status is DownloadStatus.CANCELED:
            self.set_text(row_index=row_index, text=EMPTY_PROGRESS_TEXT)
            return

        self.set_text(row_index=row_index, text=EMPTY_PROGRESS_TEXT)

    def set_text(self, *, row_index: int, text: str) -> None:
        self._remove_progress_cell_widget(row_index=row_index)

        table_item = self._table.item(row_index, PROGRESS_COLUMN_INDEX)

        if table_item is None:
            table_item = QTableWidgetItem(text)
            self._table.setItem(row_index, PROGRESS_COLUMN_INDEX, table_item)
        else:
            table_item.setText(text)

        table_item.setToolTip(text)

    def _ensure_progress_bar(self, *, row_index: int) -> QProgressBar:
        progress_cell_widget = self._table.cellWidget(row_index, PROGRESS_COLUMN_INDEX)

        if isinstance(progress_cell_widget, QProgressBar):
            return progress_cell_widget

        self._remove_progress_cell_widget(row_index=row_index)

        progress_bar = QProgressBar(self._table)
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("0%")
        progress_bar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._table.setCellWidget(row_index, PROGRESS_COLUMN_INDEX, progress_bar)

        return progress_bar

    def _remove_progress_cell_widget(self, *, row_index: int) -> None:
        progress_cell_widget = self._table.cellWidget(row_index, PROGRESS_COLUMN_INDEX)

        if progress_cell_widget is None:
            return

        self._table.removeCellWidget(row_index, PROGRESS_COLUMN_INDEX)
        progress_cell_widget.deleteLater()
