from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import override
from uuid import UUID

from PyQt6.QtCore import QEvent, QItemSelectionModel, QModelIndex, QPoint, Qt
from PyQt6.QtGui import (
    QContextMenuEvent,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QResizeEvent,
)
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QWidget

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.ui.widgets.download_queue_clipboard_presenter import (
    DownloadQueueClipboardPresenter,
)
from yaloader.ui.widgets.download_queue_columns import QUEUE_ROW_HEIGHT
from yaloader.ui.widgets.download_queue_context_menu import (
    DownloadQueueContextAction,
    show_download_queue_context_menu,
)
from yaloader.ui.widgets.download_queue_progress_presenter import (
    EMPTY_PROGRESS_TEXT,
    DownloadQueueProgressPresenter,
)
from yaloader.ui.widgets.download_queue_quality_presenter import DownloadQueueQualityPresenter
from yaloader.ui.widgets.download_queue_row_presenter import DownloadQueueRowPresenter
from yaloader.ui.widgets.download_queue_row_state import QueueTableRowState
from yaloader.ui.widgets.download_queue_selection import (
    clear_current_cell_focus,
    get_selected_rows,
    is_row_selected,
    prepare_right_click_selection,
)
from yaloader.ui.widgets.download_queue_table_config import (
    configure_download_queue_table,
    resize_download_queue_table_columns_to_viewport,
)
from yaloader.ui.widgets.download_queue_url_presenter import DownloadQueueUrlPresenter


class DownloadQueueTable(QTableWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._task_ids_by_row: dict[int, UUID] = {}
        self._row_by_task_id: dict[UUID, int] = {}
        self._row_states_by_task_id: dict[UUID, QueueTableRowState] = {}

        self._on_download_tasks: Callable[[tuple[UUID, ...]], None] | None = None
        self._on_cancel_task: Callable[[UUID], None] | None = None
        self._on_remove_tasks: Callable[[tuple[UUID, ...]], None] | None = None
        self._suppress_next_context_menu_event = False

        self._url_presenter = DownloadQueueUrlPresenter(
            table=self,
            row_by_task_id=self._row_by_task_id,
            row_states_by_task_id=self._row_states_by_task_id,
        )
        self._quality_presenter = DownloadQueueQualityPresenter(
            table=self,
            row_by_task_id=self._row_by_task_id,
            row_states_by_task_id=self._row_states_by_task_id,
            parent=self,
        )
        self._progress_presenter = DownloadQueueProgressPresenter(
            table=self,
            row_by_task_id=self._row_by_task_id,
        )
        self._clipboard_presenter = DownloadQueueClipboardPresenter(
            url_presenter=self._url_presenter,
            row_states_by_task_id=self._row_states_by_task_id,
        )
        self._row_presenter = DownloadQueueRowPresenter(
            table=self,
            quality_presenter=self._quality_presenter,
            url_presenter=self._url_presenter,
        )

        configure_download_queue_table(table=self)

    @override
    def viewportEvent(self, event: QEvent | None) -> bool:
        if event is None:
            return super().viewportEvent(event)

        if (
            event.type() == QEvent.Type.MouseButtonPress
            and isinstance(event, QMouseEvent)
            and self._handle_viewport_mouse_press(event=event)
        ):
            return True

        if event.type() == QEvent.Type.ContextMenu and isinstance(event, QContextMenuEvent):
            if self._suppress_next_context_menu_event:
                self._suppress_next_context_menu_event = False
                event.accept()
                return True

            return self._handle_viewport_context_menu(event=event)

        return super().viewportEvent(event)

    @override
    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self.resize_columns_to_viewport()

    @override
    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if event is not None and event.matches(QKeySequence.StandardKey.Copy):
            self._copy_selected_urls_to_clipboard()
            event.accept()
            return

        super().keyPressEvent(event)

    @override
    def selectionCommand(
        self,
        index: QModelIndex,
        event: QEvent | None = None,
    ) -> QItemSelectionModel.SelectionFlag:
        if not isinstance(event, QMouseEvent) or event.button() != Qt.MouseButton.RightButton:
            return super().selectionCommand(index, event)

        if index.isValid() and self._is_row_selected(row_index=index.row()):
            return QItemSelectionModel.SelectionFlag.NoUpdate

        return QItemSelectionModel.SelectionFlag.ClearAndSelect

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
        self.setRowHeight(row_index, QUEUE_ROW_HEIGHT)

        self._task_ids_by_row[row_index] = task.task_id
        self._row_by_task_id[task.task_id] = row_index
        self._row_states_by_task_id[task.task_id] = QueueTableRowState.create(task=task)

        self._row_presenter.set_task_row_values(row_index=row_index, task=task)
        self._progress_presenter.set_text(row_index=row_index, text=EMPTY_PROGRESS_TEXT)
        self.resize_columns_to_viewport()

    def update_task(self, task: DownloadTask) -> None:
        row_index = self._row_by_task_id.get(task.task_id)
        row_state = self._row_states_by_task_id.get(task.task_id)

        if row_index is None or row_state is None:
            return

        self._quality_presenter.clear_pending_if_task_is_not_pending(task=task)
        self._url_presenter.clear_metadata_resolution_failed_if_title_exists(task=task)

        updated_row_state = self._row_states_by_task_id.get(task.task_id)

        if updated_row_state is None:
            return

        self._row_states_by_task_id[task.task_id] = updated_row_state.with_task(task=task)

        self.setRowHeight(row_index, QUEUE_ROW_HEIGHT)
        self._row_presenter.set_task_row_values(row_index=row_index, task=task)
        self._progress_presenter.sync_with_task_status(row_index=row_index, task=task)
        self._quality_presenter.sync_timer()
        self.resize_columns_to_viewport()

    def reload_tasks(self, tasks: Sequence[DownloadTask]) -> None:
        previous_row_states = self._row_states_by_task_id.copy()

        self.setRowCount(0)
        self._task_ids_by_row.clear()
        self._row_by_task_id.clear()
        self._row_states_by_task_id.clear()
        self._quality_presenter.sync_timer()

        for task in tasks:
            previous_row_state = previous_row_states.get(task.task_id)
            self.append_task(task)

            if previous_row_state is None:
                continue

            if previous_row_state.is_quality_resolution_pending:
                self.mark_quality_resolution_pending(task_id=task.task_id)

            if previous_row_state.is_metadata_resolution_failed:
                self.mark_metadata_resolution_failed(task_id=task.task_id)

        self.resize_columns_to_viewport()

    def has_tasks(self) -> bool:
        return self.rowCount() > 0

    def get_selected_task_ids(self) -> tuple[UUID, ...]:
        selected_rows = self._get_selected_rows()
        task_ids: list[UUID] = []

        for row_index in selected_rows:
            task_id = self._task_ids_by_row.get(row_index)

            if task_id is not None:
                task_ids.append(task_id)

        return tuple(task_ids)

    def mark_quality_resolution_pending(self, *, task_id: UUID) -> None:
        self._quality_presenter.mark_pending(task_id=task_id)

    def clear_quality_resolution_pending(self, *, task_id: UUID) -> None:
        self._quality_presenter.clear_pending(task_id=task_id)

    def mark_metadata_resolution_failed(self, *, task_id: UUID) -> None:
        self._url_presenter.mark_metadata_resolution_failed(task_id=task_id)

    def prepare_tasks_for_download(self, *, task_ids: tuple[UUID, ...]) -> None:
        self._progress_presenter.prepare_tasks_for_download(task_ids=task_ids)

    def set_task_progress(self, progress: DownloadProgress) -> None:
        self._progress_presenter.set_task_progress(progress=progress)

    def resize_columns_to_viewport(self) -> None:
        resize_download_queue_table_columns_to_viewport(table=self)

    def _handle_viewport_mouse_press(self, *, event: QMouseEvent) -> bool:
        clicked_position = event.position().toPoint()
        clicked_item = self.itemAt(clicked_position)

        if event.button() == Qt.MouseButton.LeftButton and clicked_item is None:
            self._clear_current_cell_focus()
            self.clearFocus()
            event.accept()
            return True

        if event.button() != Qt.MouseButton.RightButton:
            return False

        if clicked_item is None:
            self._clear_current_cell_focus()
            event.accept()
            return True

        self._prepare_right_click_selection(clicked_item=clicked_item)

        self._suppress_next_context_menu_event = True
        self._show_context_menu(
            global_position=event.globalPosition().toPoint(),
            clicked_row_index=clicked_item.row(),
        )

        event.accept()
        return True

    def _handle_viewport_context_menu(self, *, event: QContextMenuEvent) -> bool:
        table_item = self.itemAt(event.pos())

        if table_item is None:
            self._clear_current_cell_focus()
            event.accept()
            return True

        self._prepare_right_click_selection(clicked_item=table_item)
        self._show_context_menu(
            global_position=event.globalPos(),
            clicked_row_index=table_item.row(),
        )

        event.accept()
        return True

    def _prepare_right_click_selection(self, *, clicked_item: QTableWidgetItem) -> None:
        prepare_right_click_selection(table=self, clicked_item=clicked_item)

    def _show_context_menu(self, *, global_position: QPoint, clicked_row_index: int) -> None:
        selected_task_ids = self._get_context_task_ids(clicked_row_index=clicked_row_index)
        selected_tasks = self._get_tasks_by_ids(task_ids=selected_task_ids)

        menu_result = show_download_queue_context_menu(
            parent=self,
            global_position=global_position,
            selected_tasks=selected_tasks,
            selected_task_ids=selected_task_ids,
        )

        if menu_result is None:
            return

        if menu_result.action is DownloadQueueContextAction.COPY:
            self._copy_task_urls_to_clipboard(
                tasks=self._get_tasks_by_ids(task_ids=menu_result.task_ids)
            )
            return

        if menu_result.action is DownloadQueueContextAction.CANCEL:
            self._cancel_task(menu_result.task_ids[0])
            return

        if menu_result.action is DownloadQueueContextAction.DOWNLOAD:
            self._download_tasks(menu_result.task_ids)
            return

        if menu_result.action is DownloadQueueContextAction.REMOVE:
            self._remove_tasks(menu_result.task_ids)

    def _get_context_task_ids(self, *, clicked_row_index: int) -> tuple[UUID, ...]:
        selected_task_ids = self.get_selected_task_ids()

        if selected_task_ids and self._is_row_selected(row_index=clicked_row_index):
            return selected_task_ids

        clicked_task_id = self._task_ids_by_row.get(clicked_row_index)

        if clicked_task_id is None:
            return ()

        return (clicked_task_id,)

    def _get_selected_rows(self) -> tuple[int, ...]:
        return get_selected_rows(table=self)

    def _is_row_selected(self, *, row_index: int) -> bool:
        return is_row_selected(table=self, row_index=row_index)

    def _get_tasks_by_ids(self, *, task_ids: tuple[UUID, ...]) -> tuple[DownloadTask, ...]:
        tasks: list[DownloadTask] = []

        for task_id in task_ids:
            row_state = self._row_states_by_task_id.get(task_id)

            if row_state is not None:
                tasks.append(row_state.task)

        return tuple(tasks)

    def _download_tasks(self, task_ids: tuple[UUID, ...]) -> None:
        if self._on_download_tasks is not None:
            self._on_download_tasks(task_ids)

    def _cancel_task(self, task_id: UUID) -> None:
        if self._on_cancel_task is not None:
            self._on_cancel_task(task_id)

    def _remove_tasks(self, task_ids: tuple[UUID, ...]) -> None:
        if self._on_remove_tasks is not None:
            self._on_remove_tasks(task_ids)

    def _copy_selected_urls_to_clipboard(self) -> None:
        selected_tasks = self._get_tasks_by_ids(task_ids=self.get_selected_task_ids())

        if not selected_tasks:
            return

        self._copy_task_urls_to_clipboard(tasks=selected_tasks)

    def _copy_task_urls_to_clipboard(self, *, tasks: tuple[DownloadTask, ...]) -> None:
        self._clipboard_presenter.copy_tasks_to_clipboard(tasks=tasks)

    def _clear_current_cell_focus(self) -> None:
        clear_current_cell_focus(table=self)
