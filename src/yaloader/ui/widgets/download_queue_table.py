from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import cast, override
from uuid import UUID

from PyQt6.QtCore import QEvent, QItemSelectionModel, QModelIndex, QPoint, Qt, QTimer
from PyQt6.QtGui import (
    QClipboard,
    QContextMenuEvent,
    QGuiApplication,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QResizeEvent,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus
from yaloader.ui.widgets.download_queue_columns import (
    FOLDER_COLUMN_INDEX,
    FORMAT_COLUMN_INDEX,
    MODE_COLUMN_INDEX,
    PROGRESS_COLUMN_INDEX,
    QUALITY_COLUMN_INDEX,
    QUEUE_COLUMN_COUNT,
    QUEUE_ROW_HEIGHT,
    STATUS_COLUMN_INDEX,
    TABLE_RIGHT_OVERDRAW_WIDTH,
    URL_COLUMN_INDEX,
    calculate_queue_column_widths,
)
from yaloader.ui.widgets.download_queue_context_menu import (
    DownloadQueueContextAction,
    show_download_queue_context_menu,
)
from yaloader.ui.widgets.download_queue_delegate import (
    URL_COPY_FEEDBACK_ROLE,
    URL_TITLE_ROLE,
    URL_TITLE_STATE_DEFAULT,
    URL_TITLE_STATE_ERROR,
    URL_TITLE_STATE_ROLE,
    DownloadQueueItemDelegate,
)

EMPTY_PROGRESS_TEXT = "—"

QUALITY_RESOLUTION_ANIMATION_INTERVAL_MS = 420
QUALITY_RESOLUTION_TOOLTIP = "Определяем доступное качество"
QUALITY_RESOLUTION_TEXT_STATES = (
    "Checking.",
    "Checking..",
    "Checking...",
)

COPY_FEEDBACK_DURATION_MS = 1000
COPY_FEEDBACK_TEXT = "Ссылка скопирована..."
METADATA_RESOLUTION_FAILED_TEXT = "Ссылку не удалось определить..."


class DownloadQueueTable(QTableWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._task_ids_by_row: dict[int, UUID] = {}
        self._row_by_task_id: dict[UUID, int] = {}
        self._tasks_by_id: dict[UUID, DownloadTask] = {}
        self._quality_resolution_task_ids: set[UUID] = set()
        self._metadata_resolution_failed_task_ids: set[UUID] = set()
        self._quality_resolution_step_index = 0
        self._quality_resolution_timer = QTimer(self)

        self._copy_feedback_generation = 0
        self._copy_feedback_generation_by_task_id: dict[UUID, int] = {}

        self._on_download_tasks: Callable[[tuple[UUID, ...]], None] | None = None
        self._on_cancel_task: Callable[[UUID], None] | None = None
        self._on_remove_tasks: Callable[[tuple[UUID, ...]], None] | None = None
        self._suppress_next_context_menu_event = False

        self._configure_table()
        self._configure_quality_resolution_timer()

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
        self._tasks_by_id[task.task_id] = task

        self._set_task_row_values(row_index=row_index, task=task)
        self._set_progress_text(row_index=row_index, text=EMPTY_PROGRESS_TEXT)
        self.resize_columns_to_viewport()

    def update_task(self, task: DownloadTask) -> None:
        row_index = self._row_by_task_id.get(task.task_id)

        if row_index is None:
            return

        if task.status is not DownloadStatus.PENDING:
            self._quality_resolution_task_ids.discard(task.task_id)
            self._sync_quality_resolution_timer()

        if self._normalize_task_title(task=task) is not None:
            self._metadata_resolution_failed_task_ids.discard(task.task_id)

        self._tasks_by_id[task.task_id] = task
        self.setRowHeight(row_index, QUEUE_ROW_HEIGHT)
        self._set_task_row_values(row_index=row_index, task=task)
        self._sync_progress_cell_with_status(row_index=row_index, task=task)
        self.resize_columns_to_viewport()

    def reload_tasks(self, tasks: Sequence[DownloadTask]) -> None:
        pending_quality_task_ids = self._quality_resolution_task_ids.copy()
        metadata_resolution_failed_task_ids = self._metadata_resolution_failed_task_ids.copy()

        self.setRowCount(0)
        self._task_ids_by_row.clear()
        self._row_by_task_id.clear()
        self._tasks_by_id.clear()
        self._quality_resolution_task_ids.clear()
        self._metadata_resolution_failed_task_ids.clear()
        self._copy_feedback_generation_by_task_id.clear()
        self._sync_quality_resolution_timer()

        for task in tasks:
            self.append_task(task)

            if task.task_id in pending_quality_task_ids:
                self.mark_quality_resolution_pending(task_id=task.task_id)

            if task.task_id in metadata_resolution_failed_task_ids:
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
        row_index = self._row_by_task_id.get(task_id)
        task = self._tasks_by_id.get(task_id)

        if row_index is None or task is None:
            return

        if task.status is not DownloadStatus.PENDING:
            return

        self._quality_resolution_task_ids.add(task_id)
        self._set_quality_cell_text(
            row_index=row_index,
            text=self._build_quality_resolution_text(),
            tooltip=QUALITY_RESOLUTION_TOOLTIP,
        )
        self._sync_quality_resolution_timer()

    def clear_quality_resolution_pending(self, *, task_id: UUID) -> None:
        was_pending = task_id in self._quality_resolution_task_ids
        self._quality_resolution_task_ids.discard(task_id)
        self._sync_quality_resolution_timer()

        if not was_pending:
            return

        row_index = self._row_by_task_id.get(task_id)
        task = self._tasks_by_id.get(task_id)

        if row_index is None or task is None:
            return

        self._set_quality_cell_text(
            row_index=row_index,
            text=task.video_quality.value,
            tooltip=task.video_quality.value,
        )

    def mark_metadata_resolution_failed(self, *, task_id: UUID) -> None:
        row_index = self._row_by_task_id.get(task_id)
        task = self._tasks_by_id.get(task_id)

        if row_index is None or task is None:
            return

        self._metadata_resolution_failed_task_ids.add(task_id)
        self._set_url_secondary_text(
            row_index=row_index,
            text=METADATA_RESOLUTION_FAILED_TEXT,
            state=URL_TITLE_STATE_ERROR,
            tooltip=f"{task.url.value}\n{METADATA_RESOLUTION_FAILED_TEXT}",
        )

    def prepare_tasks_for_download(self, *, task_ids: tuple[UUID, ...]) -> None:
        for task_id in task_ids:
            row_index = self._row_by_task_id.get(task_id)

            if row_index is None:
                continue

            progress_bar_widget = self._ensure_progress_bar(row_index=row_index)
            progress_bar_widget.setRange(0, 100)
            progress_bar_widget.setValue(0)
            progress_bar_widget.setFormat("0%")

    def set_task_progress(self, progress: DownloadProgress) -> None:
        row_index = self._row_by_task_id.get(progress.task_id)

        if row_index is None:
            return

        progress_bar_widget = self._ensure_progress_bar(row_index=row_index)

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
        available_width = viewport.width() + TABLE_RIGHT_OVERDRAW_WIDTH
        column_widths = calculate_queue_column_widths(available_width=available_width)

        for column_index, column_width in column_widths.items():
            self.setColumnWidth(column_index, column_width)

    def _configure_table(self) -> None:
        self.setColumnCount(QUEUE_COLUMN_COUNT)
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
        self.setItemDelegate(DownloadQueueItemDelegate(self))
        self.setAlternatingRowColors(True)
        self.setMouseTracking(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWordWrap(False)

        horizontal_header = cast(QHeaderView, self.horizontalHeader())
        horizontal_header.setSectionsMovable(False)
        horizontal_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        horizontal_header.setStretchLastSection(False)

        vertical_header = cast(QHeaderView, self.verticalHeader())
        vertical_header.hide()
        vertical_header.setDefaultSectionSize(QUEUE_ROW_HEIGHT)
        vertical_header.setMinimumSectionSize(QUEUE_ROW_HEIGHT)
        vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        self.resize_columns_to_viewport()

    def _configure_quality_resolution_timer(self) -> None:
        self._quality_resolution_timer.setInterval(QUALITY_RESOLUTION_ANIMATION_INTERVAL_MS)
        self._quality_resolution_timer.timeout.connect(self._advance_quality_resolution_animation)

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
        row_index = clicked_item.row()

        if not self._is_row_selected(row_index=row_index):
            self.clearSelection()
            self.selectRow(row_index)

        self.setFocus()

        viewport = cast(QWidget, self.viewport())
        viewport.update()

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
        selection_model = self.selectionModel()

        if isinstance(selection_model, QItemSelectionModel):
            selected_rows = sorted({index.row() for index in selection_model.selectedRows()})

            if selected_rows:
                return tuple(selected_rows)

        return tuple(sorted({index.row() for index in self.selectedIndexes()}))

    def _is_row_selected(self, *, row_index: int) -> bool:
        return row_index in self._get_selected_rows()

    def _get_tasks_by_ids(self, *, task_ids: tuple[UUID, ...]) -> tuple[DownloadTask, ...]:
        tasks: list[DownloadTask] = []

        for task_id in task_ids:
            task = self._tasks_by_id.get(task_id)

            if task is not None:
                tasks.append(task)

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
        urls_text = "\n".join(task.url.value for task in tasks)
        clipboard = QGuiApplication.clipboard()

        if not isinstance(clipboard, QClipboard):
            return

        clipboard.setText(urls_text)
        self._show_inline_copy_feedback(task_ids=tuple(task.task_id for task in tasks))

    def _show_inline_copy_feedback(self, *, task_ids: tuple[UUID, ...]) -> None:
        if not task_ids:
            return

        self._copy_feedback_generation += 1
        generation = self._copy_feedback_generation

        for task_id in task_ids:
            self._copy_feedback_generation_by_task_id[task_id] = generation
            self._set_url_copy_feedback(task_id=task_id, text=COPY_FEEDBACK_TEXT)

        QTimer.singleShot(
            COPY_FEEDBACK_DURATION_MS,
            lambda: self._clear_inline_copy_feedback(
                task_ids=task_ids,
                generation=generation,
            ),
        )

    def _clear_inline_copy_feedback(
        self,
        *,
        task_ids: tuple[UUID, ...],
        generation: int,
    ) -> None:
        for task_id in task_ids:
            if self._copy_feedback_generation_by_task_id.get(task_id) != generation:
                continue

            self._copy_feedback_generation_by_task_id.pop(task_id, None)
            self._set_url_copy_feedback(task_id=task_id, text=None)

    def _set_url_copy_feedback(self, *, task_id: UUID, text: str | None) -> None:
        row_index = self._row_by_task_id.get(task_id)

        if row_index is None:
            return

        table_item = self.item(row_index, URL_COLUMN_INDEX)

        if table_item is None:
            return

        table_item.setData(URL_COPY_FEEDBACK_ROLE, text)

        viewport = cast(QWidget, self.viewport())
        viewport.update()

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
            QUALITY_COLUMN_INDEX: self._build_quality_cell_text(task=task),
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

            if column_index == URL_COLUMN_INDEX:
                self._configure_url_item(
                    row_index=row_index,
                    table_item=table_item,
                    task=task,
                )
                continue

            if (
                column_index == QUALITY_COLUMN_INDEX
                and task.task_id in self._quality_resolution_task_ids
            ):
                table_item.setToolTip(QUALITY_RESOLUTION_TOOLTIP)
            else:
                table_item.setToolTip(value)

    def _configure_url_item(
        self,
        *,
        row_index: int,
        table_item: QTableWidgetItem,
        task: DownloadTask,
    ) -> None:
        if task.task_id in self._metadata_resolution_failed_task_ids:
            self._set_url_secondary_text(
                row_index=row_index,
                text=METADATA_RESOLUTION_FAILED_TEXT,
                state=URL_TITLE_STATE_ERROR,
                tooltip=f"{task.url.value}\n{METADATA_RESOLUTION_FAILED_TEXT}",
            )
            return

        normalized_title = self._normalize_task_title(task=task)

        if normalized_title is None:
            table_item.setData(URL_TITLE_ROLE, None)
            table_item.setData(URL_TITLE_STATE_ROLE, URL_TITLE_STATE_DEFAULT)
            table_item.setToolTip(task.url.value)
            return

        self._set_url_secondary_text(
            row_index=row_index,
            text=normalized_title,
            state=URL_TITLE_STATE_DEFAULT,
            tooltip=f"{task.url.value}\n{normalized_title}",
        )

    def _set_url_secondary_text(
        self,
        *,
        row_index: int,
        text: str,
        state: str,
        tooltip: str,
    ) -> None:
        table_item = self.item(row_index, URL_COLUMN_INDEX)

        if table_item is None:
            return

        table_item.setData(URL_TITLE_ROLE, text)
        table_item.setData(URL_TITLE_STATE_ROLE, state)
        table_item.setToolTip(tooltip)

        viewport = cast(QWidget, self.viewport())
        viewport.update()

    def _normalize_task_title(self, *, task: DownloadTask) -> str | None:
        if task.title is None:
            return None

        normalized_title = task.title.strip()

        if not normalized_title:
            return None

        return normalized_title

    def _build_quality_cell_text(self, *, task: DownloadTask) -> str:
        if task.task_id in self._quality_resolution_task_ids:
            return self._build_quality_resolution_text()

        return task.video_quality.value

    def _set_quality_cell_text(
        self,
        *,
        row_index: int,
        text: str,
        tooltip: str,
    ) -> None:
        table_item = self.item(row_index, QUALITY_COLUMN_INDEX)

        if table_item is None:
            table_item = QTableWidgetItem(text)
            self.setItem(row_index, QUALITY_COLUMN_INDEX, table_item)
        else:
            table_item.setText(text)

        table_item.setToolTip(tooltip)

    def _advance_quality_resolution_animation(self) -> None:
        if not self._quality_resolution_task_ids:
            self._sync_quality_resolution_timer()
            return

        self._quality_resolution_step_index = (self._quality_resolution_step_index + 1) % len(
            QUALITY_RESOLUTION_TEXT_STATES
        )
        text = self._build_quality_resolution_text()
        missing_task_ids: list[UUID] = []

        for task_id in tuple(self._quality_resolution_task_ids):
            row_index = self._row_by_task_id.get(task_id)

            if row_index is None:
                missing_task_ids.append(task_id)
                continue

            self._set_quality_cell_text(
                row_index=row_index,
                text=text,
                tooltip=QUALITY_RESOLUTION_TOOLTIP,
            )

        for task_id in missing_task_ids:
            self._quality_resolution_task_ids.discard(task_id)

        self._sync_quality_resolution_timer()

    def _build_quality_resolution_text(self) -> str:
        return QUALITY_RESOLUTION_TEXT_STATES[self._quality_resolution_step_index]

    def _sync_quality_resolution_timer(self) -> None:
        if self._quality_resolution_task_ids:
            if not self._quality_resolution_timer.isActive():
                self._quality_resolution_timer.start()
            return

        if self._quality_resolution_timer.isActive():
            self._quality_resolution_timer.stop()

    def _sync_progress_cell_with_status(self, *, row_index: int, task: DownloadTask) -> None:
        if task.status is DownloadStatus.COMPLETED:
            progress_bar_widget = self._ensure_progress_bar(row_index=row_index)
            progress_bar_widget.setRange(0, 100)
            progress_bar_widget.setValue(100)
            progress_bar_widget.setFormat("100%")
            return

        if task.status is DownloadStatus.RUNNING:
            progress_bar_widget = self._ensure_progress_bar(row_index=row_index)
            progress_bar_widget.setRange(0, 100)
            progress_bar_widget.setValue(0)
            progress_bar_widget.setFormat("0%")
            return

        if task.status is DownloadStatus.FAILED:
            self._set_progress_text(row_index=row_index, text="Ошибка")
            return

        if task.status is DownloadStatus.CANCELED:
            self._set_progress_text(row_index=row_index, text=EMPTY_PROGRESS_TEXT)
            return

        self._set_progress_text(row_index=row_index, text=EMPTY_PROGRESS_TEXT)

    def _ensure_progress_bar(self, *, row_index: int) -> QProgressBar:
        progress_bar_widget = self.cellWidget(row_index, PROGRESS_COLUMN_INDEX)

        if isinstance(progress_bar_widget, QProgressBar):
            return progress_bar_widget

        self._remove_progress_cell_widget(row_index=row_index)

        progress_bar = QProgressBar(self)
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("0%")
        progress_bar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.setCellWidget(row_index, PROGRESS_COLUMN_INDEX, progress_bar)

        return progress_bar

    def _set_progress_text(self, *, row_index: int, text: str) -> None:
        self._remove_progress_cell_widget(row_index=row_index)

        table_item = self.item(row_index, PROGRESS_COLUMN_INDEX)

        if table_item is None:
            table_item = QTableWidgetItem(text)
            self.setItem(row_index, PROGRESS_COLUMN_INDEX, table_item)
        else:
            table_item.setText(text)

        table_item.setToolTip(text)

    def _remove_progress_cell_widget(self, *, row_index: int) -> None:
        progress_cell_widget = self.cellWidget(row_index, PROGRESS_COLUMN_INDEX)

        if progress_cell_widget is None:
            return

        self.removeCellWidget(row_index, PROGRESS_COLUMN_INDEX)
        progress_cell_widget.deleteLater()
