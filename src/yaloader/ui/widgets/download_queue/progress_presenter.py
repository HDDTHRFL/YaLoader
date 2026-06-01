from __future__ import annotations

from uuid import UUID

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QProgressBar, QTableWidget, QTableWidgetItem

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.domain.download_speed_limit import format_bytes_per_second
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus
from yaloader.ui.widgets.download_queue.columns import STATUS_PROGRESS_COLUMN_INDEX

STATUS_TEXT_BY_STATUS = {
    DownloadStatus.PENDING: DownloadStatus.PENDING.value,
    DownloadStatus.RUNNING: DownloadStatus.RUNNING.value,
    DownloadStatus.COMPLETED: DownloadStatus.COMPLETED.value,
    DownloadStatus.FAILED: DownloadStatus.FAILED.value,
    DownloadStatus.CANCELED: DownloadStatus.CANCELED.value,
}

EMPTY_PROGRESS_TEXT = DownloadStatus.PENDING.value
PROCESSING_STATUS_TEXT = "Обработка"


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
            progress_bar.setToolTip(progress.status_text)
            return

        progress_bar.setRange(0, 100)
        progress_bar.setValue(progress.progress_bar_value)

        progress_text = self._build_progress_bar_text(progress=progress)
        progress_bar.setFormat(progress_text)
        progress_bar.setToolTip(progress_text)

    def sync_with_task_status(self, *, row_index: int, task: DownloadTask) -> None:
        if task.status is DownloadStatus.RUNNING:
            progress_bar = self._ensure_progress_bar(row_index=row_index)
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setFormat("0%")
            return

        self.set_text(
            row_index=row_index,
            text=STATUS_TEXT_BY_STATUS[task.status],
        )

    def set_text(self, *, row_index: int, text: str) -> None:
        self._remove_progress_cell_widget(row_index=row_index)

        table_item = self._table.item(row_index, STATUS_PROGRESS_COLUMN_INDEX)

        if table_item is None:
            table_item = QTableWidgetItem(text)
            self._table.setItem(row_index, STATUS_PROGRESS_COLUMN_INDEX, table_item)
        else:
            table_item.setText(text)

        table_item.setToolTip(text)

    def _build_progress_bar_text(self, *, progress: DownloadProgress) -> str:
        if progress.status_text == PROCESSING_STATUS_TEXT:
            return PROCESSING_STATUS_TEXT

        progress_text = f"{progress.progress_bar_value}%"

        if progress.speed_bytes_per_second is None:
            return progress_text

        return (
            f"{progress_text} · "
            f"{format_bytes_per_second(bytes_per_second=progress.speed_bytes_per_second)}"
        )

    def _ensure_progress_bar(self, *, row_index: int) -> QProgressBar:
        progress_cell_widget = self._table.cellWidget(row_index, STATUS_PROGRESS_COLUMN_INDEX)

        if isinstance(progress_cell_widget, QProgressBar):
            return progress_cell_widget

        self._remove_progress_cell_widget(row_index=row_index)

        progress_bar = QProgressBar(self._table)
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("0%")
        progress_bar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._table.setCellWidget(row_index, STATUS_PROGRESS_COLUMN_INDEX, progress_bar)

        return progress_bar

    def _remove_progress_cell_widget(self, *, row_index: int) -> None:
        progress_cell_widget = self._table.cellWidget(row_index, STATUS_PROGRESS_COLUMN_INDEX)

        if progress_cell_widget is None:
            return

        self._table.removeCellWidget(row_index, STATUS_PROGRESS_COLUMN_INDEX)
        progress_cell_widget.deleteLater()
