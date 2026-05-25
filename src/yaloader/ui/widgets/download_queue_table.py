from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import cast, override
from uuid import UUID

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus

MODE_COLUMN_INDEX = 0
URL_COLUMN_INDEX = 1
QUALITY_COLUMN_INDEX = 2
FORMAT_COLUMN_INDEX = 3
STATUS_COLUMN_INDEX = 4
PROGRESS_COLUMN_INDEX = 5
FOLDER_COLUMN_INDEX = 6

TABLE_WIDTH_SAFETY_MARGIN = 6

MIN_COLUMN_WIDTHS = {
    MODE_COLUMN_INDEX: 64,
    URL_COLUMN_INDEX: 260,
    QUALITY_COLUMN_INDEX: 84,
    FORMAT_COLUMN_INDEX: 68,
    STATUS_COLUMN_INDEX: 92,
    PROGRESS_COLUMN_INDEX: 120,
    FOLDER_COLUMN_INDEX: 170,
}

COLUMN_STRETCH_WEIGHTS = {
    MODE_COLUMN_INDEX: 0.2,
    URL_COLUMN_INDEX: 6.0,
    QUALITY_COLUMN_INDEX: 0.25,
    FORMAT_COLUMN_INDEX: 0.25,
    STATUS_COLUMN_INDEX: 0.35,
    PROGRESS_COLUMN_INDEX: 1.1,
    FOLDER_COLUMN_INDEX: 2.4,
}


class DownloadQueueTable(QTableWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._task_ids_by_row: dict[int, UUID] = {}
        self._row_by_task_id: dict[UUID, int] = {}
        self._on_download_task: Callable[[UUID], None] | None = None
        self._on_remove_task: Callable[[UUID], None] | None = None

        self._configure_table()

    @override
    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self.resize_columns_to_viewport()

    def set_context_menu_callbacks(
        self,
        *,
        on_download_task: Callable[[UUID], None],
        on_remove_task: Callable[[UUID], None],
    ) -> None:
        self._on_download_task = on_download_task
        self._on_remove_task = on_remove_task

    def append_task(self, task: DownloadTask) -> None:
        row_index = self.rowCount()
        self.insertRow(row_index)
        self._task_ids_by_row[row_index] = task.task_id
        self._row_by_task_id[task.task_id] = row_index

        self._set_task_row_values(row_index=row_index, task=task)
        self._set_progress_bar(row_index=row_index, task=task)
        self.resizeRowsToContents()
        self.resize_columns_to_viewport()

    def update_task(self, task: DownloadTask) -> None:
        row_index = self._row_by_task_id.get(task.task_id)

        if row_index is None:
            return

        self._set_task_row_values(row_index=row_index, task=task)
        self._sync_progress_bar_with_status(row_index=row_index, task=task)
        self.resizeRowsToContents()
        self.resize_columns_to_viewport()

    def reload_tasks(self, tasks: Sequence[DownloadTask]) -> None:
        self.setRowCount(0)
        self._task_ids_by_row.clear()
        self._row_by_task_id.clear()

        for task in tasks:
            self.append_task(task)

        self.resize_columns_to_viewport()

    def get_selected_task_id(self) -> UUID | None:
        row_index = self.currentRow()

        if row_index < 0:
            return None

        return self._task_ids_by_row.get(row_index)

    def set_task_progress(self, progress: DownloadProgress) -> None:
        row_index = self._row_by_task_id.get(progress.task_id)

        if row_index is None:
            return

        progress_bar_widget = self.cellWidget(row_index, PROGRESS_COLUMN_INDEX)

        if not isinstance(progress_bar_widget, QProgressBar):
            return

        if progress.percent is None:
            progress_bar_widget.setRange(0, 0)
            progress_bar_widget.setFormat(progress.status_text)
            return

        progress_bar_widget.setRange(0, 100)
        progress_bar_widget.setValue(progress.progress_bar_value)
        progress_bar_widget.setFormat(f"{progress.progress_bar_value}%")

    def resize_columns_to_viewport(self) -> None:
        if self.columnCount() == 0:
            return

        viewport = cast(QWidget, self.viewport())
        available_width = viewport.width() - TABLE_WIDTH_SAFETY_MARGIN

        if available_width <= 0:
            return

        minimum_total_width = sum(MIN_COLUMN_WIDTHS.values())
        total_weight = sum(COLUMN_STRETCH_WEIGHTS.values())
        calculated_widths: dict[int, int] = {}

        if available_width <= minimum_total_width:
            scale = available_width / minimum_total_width

            for column_index, minimum_width in MIN_COLUMN_WIDTHS.items():
                calculated_widths[column_index] = max(1, int(minimum_width * scale))
        else:
            extra_width = available_width - minimum_total_width

            for column_index, minimum_width in MIN_COLUMN_WIDTHS.items():
                weighted_extra = int(
                    extra_width * COLUMN_STRETCH_WEIGHTS[column_index] / total_weight
                )
                calculated_widths[column_index] = minimum_width + weighted_extra

        last_column_width = available_width - sum(
            width
            for column_index, width in calculated_widths.items()
            if column_index != FOLDER_COLUMN_INDEX
        )
        calculated_widths[FOLDER_COLUMN_INDEX] = max(1, last_column_width)

        for column_index, column_width in calculated_widths.items():
            self.setColumnWidth(column_index, column_width)

    def _configure_table(self) -> None:
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(
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
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWordWrap(False)

        vertical_header = cast(QHeaderView, self.verticalHeader())
        vertical_header.hide()

        self.customContextMenuRequested.connect(self._show_context_menu)
        self.resize_columns_to_viewport()

    def _show_context_menu(self, position: QPoint) -> None:
        table_item = self.itemAt(position)

        if table_item is None:
            return

        row_index = table_item.row()
        task_id = self._task_ids_by_row.get(row_index)

        if task_id is None:
            return

        self.selectRow(row_index)

        context_menu = QMenu(self)
        download_action = context_menu.addAction("Скачать этот файл")
        remove_action = context_menu.addAction("Удалить из очереди")

        viewport = cast(QWidget, self.viewport())
        selected_action = context_menu.exec(viewport.mapToGlobal(position))

        if selected_action == download_action and self._on_download_task is not None:
            self._on_download_task(task_id)
            return

        if selected_action == remove_action and self._on_remove_task is not None:
            self._on_remove_task(task_id)

    def _set_task_row_values(self, *, row_index: int, task: DownloadTask) -> None:
        values_by_column = {
            MODE_COLUMN_INDEX: task.mode.value,
            URL_COLUMN_INDEX: task.url.value,
            QUALITY_COLUMN_INDEX: task.video_quality.value,
            FORMAT_COLUMN_INDEX: task.output_format.value,
            STATUS_COLUMN_INDEX: task.status.value,
            FOLDER_COLUMN_INDEX: str(task.target_dir),
        }

        for column_index, value in values_by_column.items():
            table_item = self.item(row_index, column_index)

            if table_item is None:
                table_item = QTableWidgetItem(value)
                self.setItem(row_index, column_index, table_item)
            else:
                table_item.setText(value)

            table_item.setToolTip(value)

    def _set_progress_bar(self, *, row_index: int, task: DownloadTask) -> None:
        progress_bar = QProgressBar(self)
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("0%")
        self.setCellWidget(row_index, PROGRESS_COLUMN_INDEX, progress_bar)
        self._sync_progress_bar_with_status(row_index=row_index, task=task)

    def _sync_progress_bar_with_status(self, *, row_index: int, task: DownloadTask) -> None:
        progress_bar_widget = self.cellWidget(row_index, PROGRESS_COLUMN_INDEX)

        if not isinstance(progress_bar_widget, QProgressBar):
            return

        if task.status is DownloadStatus.COMPLETED:
            progress_bar_widget.setRange(0, 100)
            progress_bar_widget.setValue(100)
            progress_bar_widget.setFormat("100%")
            return

        if task.status is DownloadStatus.RUNNING:
            return

        if task.status is DownloadStatus.FAILED:
            progress_bar_widget.setRange(0, 100)
            progress_bar_widget.setValue(0)
            progress_bar_widget.setFormat("Ошибка")
            return

        progress_bar_widget.setRange(0, 100)
        progress_bar_widget.setValue(0)
        progress_bar_widget.setFormat("0%")
