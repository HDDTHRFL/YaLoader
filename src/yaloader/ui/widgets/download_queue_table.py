from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import cast, override
from uuid import UUID

from PyQt6.QtCore import QItemSelectionModel, QModelIndex, QPoint, Qt
from PyQt6.QtGui import QAction, QFocusEvent, QMouseEvent, QPainter, QResizeEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QProgressBar,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
    QWidgetAction,
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

TABLE_WIDTH_SAFETY_MARGIN = 0

DOWNLOADABLE_STATUSES = frozenset(
    {
        DownloadStatus.PENDING,
        DownloadStatus.FAILED,
        DownloadStatus.CANCELED,
    }
)

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


class NoCellFocusItemDelegate(QStyledItemDelegate):
    @override
    def paint(
        self,
        painter: QPainter | None,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        if painter is None:
            return

        option_without_cell_focus = QStyleOptionViewItem(option)
        option_without_cell_focus.state = (
            option_without_cell_focus.state & ~QStyle.StateFlag.State_HasFocus
        )

        super().paint(painter, option_without_cell_focus, index)


class DownloadQueueTable(QTableWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._task_ids_by_row: dict[int, UUID] = {}
        self._row_by_task_id: dict[UUID, int] = {}
        self._tasks_by_id: dict[UUID, DownloadTask] = {}
        self._on_download_tasks: Callable[[tuple[UUID, ...]], None] | None = None
        self._on_cancel_task: Callable[[UUID], None] | None = None
        self._on_remove_tasks: Callable[[tuple[UUID, ...]], None] | None = None

        self._configure_table()

    @override
    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self.resize_columns_to_viewport()

    @override
    def focusOutEvent(self, event: QFocusEvent | None) -> None:
        super().focusOutEvent(event)
        self._clear_current_cell_focus()

    @override
    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            super().mousePressEvent(event)
            return

        clicked_position = event.position().toPoint()

        if event.button() == Qt.MouseButton.LeftButton and self.itemAt(clicked_position) is None:
            self._clear_current_cell_focus()
            self.clearFocus()
            event.accept()
            return

        super().mousePressEvent(event)

    def set_context_menu_callbacks(
        self,
        *,
        on_download_tasks: Callable[[tuple[UUID, ...]], None],
        on_cancel_task: Callable[[UUID], None],
        on_remove_tasks: Callable[[tuple[UUID, ...]], None],
    ) -> None:
        self._on_download_tasks = on_download_tasks
        self._on_cancel_task = on_cancel_task
        self._on_remove_tasks = on_remove_tasks

    def append_task(self, task: DownloadTask) -> None:
        row_index = self.rowCount()
        self.insertRow(row_index)
        self._task_ids_by_row[row_index] = task.task_id
        self._row_by_task_id[task.task_id] = row_index
        self._tasks_by_id[task.task_id] = task

        self._set_task_row_values(row_index=row_index, task=task)
        self._set_progress_bar(row_index=row_index, task=task)
        self.resizeRowsToContents()
        self.resize_columns_to_viewport()

    def update_task(self, task: DownloadTask) -> None:
        row_index = self._row_by_task_id.get(task.task_id)

        if row_index is None:
            return

        self._tasks_by_id[task.task_id] = task
        self._set_task_row_values(row_index=row_index, task=task)
        self._sync_progress_bar_with_status(row_index=row_index, task=task)
        self.resizeRowsToContents()
        self.resize_columns_to_viewport()

    def reload_tasks(self, tasks: Sequence[DownloadTask]) -> None:
        self.setRowCount(0)
        self._task_ids_by_row.clear()
        self._row_by_task_id.clear()
        self._tasks_by_id.clear()

        for task in tasks:
            self.append_task(task)

        self.resize_columns_to_viewport()

    def has_tasks(self) -> bool:
        return self.rowCount() > 0

    def get_selected_task_ids(self) -> tuple[UUID, ...]:
        selected_rows = sorted({index.row() for index in self.selectedIndexes()})
        task_ids: list[UUID] = []

        for row_index in selected_rows:
            task_id = self._task_ids_by_row.get(row_index)

            if task_id is not None:
                task_ids.append(task_id)

        return tuple(task_ids)

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
        self.setItemDelegate(NoCellFocusItemDelegate(self))
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
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

        if not self._is_row_selected(row_index=row_index):
            self.clearSelection()
            self.selectRow(row_index)

        selected_task_ids = self.get_selected_task_ids()

        if not selected_task_ids:
            return

        selected_tasks = self._get_tasks_by_ids(task_ids=selected_task_ids)

        if not selected_tasks:
            return

        context_menu = QMenu(self)

        download_action: QAction | None = None
        cancel_action: QAction | None = None
        remove_action: QAction | None = None
        downloadable_task_ids: tuple[UUID, ...] = ()
        cancel_task_id: UUID | None = None

        if len(selected_tasks) == 1 and selected_tasks[0].status is DownloadStatus.RUNNING:
            cancel_task_id = selected_tasks[0].task_id
            cancel_action = self._add_menu_button_action(
                menu=context_menu,
                text="Отменить загрузку",
                object_name="MenuDangerButton",
            )
        else:
            downloadable_task_ids = tuple(
                task.task_id for task in selected_tasks if task.status in DOWNLOADABLE_STATUSES
            )

            if downloadable_task_ids:
                action_text = (
                    "Скачать выбранные" if len(downloadable_task_ids) > 1 else "Скачать этот файл"
                )
                download_action = context_menu.addAction(action_text)

        remove_text = "Удалить выбранные" if len(selected_task_ids) > 1 else "Удалить из очереди"
        remove_action = self._add_menu_button_action(
            menu=context_menu,
            text=remove_text,
            object_name="MenuDangerButton",
        )

        viewport = cast(QWidget, self.viewport())
        selected_action = context_menu.exec(viewport.mapToGlobal(position))

        if selected_action is None:
            return

        if (
            cancel_action is not None
            and selected_action == cancel_action
            and cancel_task_id is not None
        ):
            self._cancel_task(cancel_task_id)
            return

        if download_action is not None and selected_action == download_action:
            self._download_tasks(downloadable_task_ids)
            return

        if remove_action is not None and selected_action == remove_action:
            self._remove_tasks(selected_task_ids)

    def _is_row_selected(self, *, row_index: int) -> bool:
        return any(index.row() == row_index for index in self.selectedIndexes())

    def _get_tasks_by_ids(self, *, task_ids: tuple[UUID, ...]) -> tuple[DownloadTask, ...]:
        tasks: list[DownloadTask] = []

        for task_id in task_ids:
            task = self._tasks_by_id.get(task_id)

            if task is not None:
                tasks.append(task)

        return tuple(tasks)

    def _add_menu_button_action(
        self,
        *,
        menu: QMenu,
        text: str,
        object_name: str,
    ) -> QWidgetAction:
        action = QWidgetAction(menu)
        button = QPushButton(text, menu)
        button.setObjectName(object_name)

        def handle_button_clicked(_checked: bool = False) -> None:
            action.trigger()
            menu.close()

        button.clicked.connect(handle_button_clicked)

        action.setDefaultWidget(button)
        menu.addAction(action)

        return action

    def _download_tasks(self, task_ids: tuple[UUID, ...]) -> None:
        if self._on_download_tasks is not None:
            self._on_download_tasks(task_ids)

    def _cancel_task(self, task_id: UUID) -> None:
        if self._on_cancel_task is not None:
            self._on_cancel_task(task_id)

    def _remove_tasks(self, task_ids: tuple[UUID, ...]) -> None:
        if self._on_remove_tasks is not None:
            self._on_remove_tasks(task_ids)

    def _clear_current_cell_focus(self) -> None:
        selection_model = self.selectionModel()

        if isinstance(selection_model, QItemSelectionModel):
            selection_model.setCurrentIndex(
                QModelIndex(),
                QItemSelectionModel.SelectionFlag.NoUpdate,
            )

        self.setCurrentIndex(QModelIndex())

        viewport = cast(QWidget, self.viewport())
        viewport.update()

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

        if task.status is DownloadStatus.CANCELED:
            progress_bar_widget.setRange(0, 100)
            progress_bar_widget.setValue(0)
            progress_bar_widget.setFormat("Отменено")
            return

        progress_bar_widget.setRange(0, 100)
        progress_bar_widget.setValue(0)
        progress_bar_widget.setFormat("0%")
