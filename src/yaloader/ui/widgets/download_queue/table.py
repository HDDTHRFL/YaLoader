from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast, override
from uuid import UUID

from PyQt6.QtCore import (
    QAbstractItemModel,
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QPoint,
    QRect,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QContextMenuEvent,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QResizeEvent,
)
from PyQt6.QtWidgets import QLabel, QScrollBar, QTableWidget, QWidget

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus
from yaloader.ui.widgets.common.overlay_scrollbar import OverlayVerticalScrollBarController
from yaloader.ui.widgets.common.url_drop_line_edit import (
    extract_first_supported_media_url_from_drop_event,
)
from yaloader.ui.widgets.download_queue.clipboard_presenter import (
    DownloadQueueClipboardPresenter,
)
from yaloader.ui.widgets.download_queue.columns import QUEUE_ROW_HEIGHT
from yaloader.ui.widgets.download_queue.context_menu import (
    DownloadQueueContextAction,
    DownloadQueueContextMenuResult,
    show_download_queue_context_menu,
)
from yaloader.ui.widgets.download_queue.drop_highlight import QueueDropHighlightOverlay
from yaloader.ui.widgets.download_queue.progress_presenter import (
    EMPTY_PROGRESS_TEXT,
    DownloadQueueProgressPresenter,
)
from yaloader.ui.widgets.download_queue.quality_presenter import DownloadQueueQualityPresenter
from yaloader.ui.widgets.download_queue.row_presenter import DownloadQueueRowPresenter
from yaloader.ui.widgets.download_queue.row_state import QueueTableRowState
from yaloader.ui.widgets.download_queue.selection import (
    clear_current_cell_focus,
    get_selected_rows,
    is_row_selected,
    prepare_right_click_selection,
)
from yaloader.ui.widgets.download_queue.table_config import (
    configure_download_queue_table,
    resize_download_queue_table_columns_to_viewport,
)
from yaloader.ui.widgets.download_queue.url_presenter import DownloadQueueUrlPresenter

QUEUE_EMPTY_HINT_TEXT = "Вставьте ссылку в поле «Ссылка» или перетащите её сюда ⬇️"
QUEUE_EMPTY_HINT_MARGIN = 36
LONG_PRESS_SELECTION_DELAY_MS = 500
LONG_PRESS_MOVE_TOLERANCE_PX = 4


def build_queue_empty_hint_label_rect(
    *,
    viewport_geometry: QRect,
    margin: int = QUEUE_EMPTY_HINT_MARGIN,
) -> QRect:
    safe_margin = max(0, margin)
    horizontal_margin = safe_margin if viewport_geometry.width() > safe_margin * 2 else 0
    vertical_margin = safe_margin if viewport_geometry.height() > safe_margin * 2 else 0

    return viewport_geometry.adjusted(
        horizontal_margin,
        vertical_margin,
        -horizontal_margin,
        -vertical_margin,
    )


QUEUE_SHORTCUT_BLOCKING_MODIFIERS = (
    Qt.KeyboardModifier.ControlModifier,
    Qt.KeyboardModifier.AltModifier,
    Qt.KeyboardModifier.MetaModifier,
)


def is_remove_selected_tasks_key_event(*, event: QKeyEvent) -> bool:
    if event.key() != Qt.Key.Key_Delete:
        return False

    modifiers = event.modifiers()

    return not has_keyboard_modifier(
        modifiers=modifiers,
        modifier=Qt.KeyboardModifier.ShiftModifier,
    ) and not has_any_keyboard_modifier(
        modifiers=modifiers,
        candidates=QUEUE_SHORTCUT_BLOCKING_MODIFIERS,
    )


def is_clear_queue_key_event(*, event: QKeyEvent) -> bool:
    if event.key() != Qt.Key.Key_Delete:
        return False

    modifiers = event.modifiers()

    return has_keyboard_modifier(
        modifiers=modifiers,
        modifier=Qt.KeyboardModifier.ShiftModifier,
    ) and not has_any_keyboard_modifier(
        modifiers=modifiers,
        candidates=QUEUE_SHORTCUT_BLOCKING_MODIFIERS,
    )


def has_keyboard_modifier(
    *,
    modifiers: Qt.KeyboardModifier,
    modifier: Qt.KeyboardModifier,
) -> bool:
    return bool(modifiers & modifier)


def has_any_keyboard_modifier(
    *,
    modifiers: Qt.KeyboardModifier,
    candidates: tuple[Qt.KeyboardModifier, ...],
) -> bool:
    return any(has_keyboard_modifier(modifiers=modifiers, modifier=modifier) for modifier in candidates)


class DownloadQueueTable(QTableWidget):
    row_selection_mode_changed = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._task_ids_by_row: dict[int, UUID] = {}
        self._row_by_task_id: dict[UUID, int] = {}
        self._row_states_by_task_id: dict[UUID, QueueTableRowState] = {}

        self._on_download_tasks: Callable[[tuple[UUID, ...]], None] | None = None
        self._on_cancel_tasks: Callable[[tuple[UUID, ...]], None] | None = None
        self._on_remove_tasks: Callable[[tuple[UUID, ...]], None] | None = None
        self._on_clear_queue: Callable[[], None] | None = None
        self._on_url_dropped: Callable[[str], None] | None = None
        self._suppress_next_context_menu_event = False
        self._vertical_row_selection_anchor_row: int | None = None
        self._left_press_row: int | None = None
        self._left_press_position: QPoint | None = None
        self._last_drag_y_position: int | None = None
        self._is_long_press_selection_active = False
        self._long_press_generation = 0

        self._empty_hint_label = self._build_empty_hint_label()
        self._drop_highlight_overlay = self._build_drop_highlight_overlay()
        self._overlay_scroll_bar_controller: OverlayVerticalScrollBarController | None = None

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
        self._overlay_scroll_bar_controller = OverlayVerticalScrollBarController(
            scroll_area=self,
        )
        self._sync_empty_hint_visibility()
        self._sync_drop_highlight_geometry()
        self._sync_overlay_scroll_bar()

    @override
    def viewportEvent(self, event: QEvent | None) -> bool:
        if event is None:
            return super().viewportEvent(event)

        if event.type() == QEvent.Type.DragEnter and isinstance(event, QDragEnterEvent):
            return self._handle_viewport_drag_enter(event=event)

        if event.type() == QEvent.Type.DragMove and isinstance(event, QDragMoveEvent):
            return self._handle_viewport_drag_move(event=event)

        if event.type() == QEvent.Type.DragLeave and isinstance(event, QDragLeaveEvent):
            return self._handle_viewport_drag_leave(event=event)

        if event.type() == QEvent.Type.Drop and isinstance(event, QDropEvent):
            return self._handle_viewport_drop(event=event)

        if (
            event.type() == QEvent.Type.MouseButtonPress
            and isinstance(event, QMouseEvent)
            and self._handle_viewport_mouse_press(event=event)
        ):
            return True

        if (
            event.type() == QEvent.Type.MouseMove
            and isinstance(event, QMouseEvent)
            and self._handle_viewport_mouse_move(event=event)
        ):
            return True

        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and isinstance(event, QMouseEvent)
            and self._handle_viewport_mouse_release(event=event)
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
    def dragEnterEvent(self, event: QDragEnterEvent | None) -> None:
        if self._accept_supported_url_drag_event(event=event):
            return

        super().dragEnterEvent(event)

    @override
    def dragMoveEvent(self, event: QDragMoveEvent | None) -> None:
        if self._accept_supported_url_drag_event(event=event):
            return

        super().dragMoveEvent(event)

    @override
    def dragLeaveEvent(self, event: QDragLeaveEvent | None) -> None:
        self._set_drop_highlight_active(is_active=False)
        super().dragLeaveEvent(event)

    @override
    def dropEvent(self, event: QDropEvent | None) -> None:
        if self._handle_supported_url_drop_event(event=event):
            return

        super().dropEvent(event)

    @override
    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self.resize_columns_to_viewport()
        self._position_empty_hint_label()
        self._sync_drop_highlight_geometry()
        self._sync_overlay_scroll_bar()

    @override
    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(0, dy)

        if dx == 0:
            return

        horizontal_scroll_bar = cast(QScrollBar, self.horizontalScrollBar())
        horizontal_scroll_bar.setValue(0)

    @override
    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if event is not None and is_clear_queue_key_event(event=event):
            self._clear_queue_from_keyboard()
            event.accept()
            return

        if event is not None and is_remove_selected_tasks_key_event(event=event):
            self._remove_selected_tasks_from_keyboard()
            event.accept()
            return

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
        on_cancel_tasks: Callable[[tuple[UUID, ...]], None],
        on_remove_tasks: Callable[[tuple[UUID, ...]], None],
        on_clear_queue: Callable[[], None],
    ) -> None:
        self._on_download_tasks = on_download_tasks
        self._on_cancel_tasks = on_cancel_tasks
        self._on_remove_tasks = on_remove_tasks
        self._on_clear_queue = on_clear_queue

    def set_url_drop_callback(self, *, on_url_dropped: Callable[[str], None]) -> None:
        self._on_url_dropped = on_url_dropped

    def append_task(self, task: DownloadTask) -> None:
        row_index = self.rowCount()
        self.insertRow(row_index)
        self.setRowHeight(row_index, QUEUE_ROW_HEIGHT)

        self._task_ids_by_row[row_index] = task.task_id
        self._row_by_task_id[task.task_id] = row_index
        self._row_states_by_task_id[task.task_id] = QueueTableRowState.create(task=task)

        self._row_presenter.set_task_row_values(
            row_index=row_index, row_state=self._row_states_by_task_id[task.task_id]
        )
        self._progress_presenter.set_text(row_index=row_index, text=EMPTY_PROGRESS_TEXT)
        self.resize_columns_to_viewport()
        self._sync_empty_hint_visibility()

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

        self._row_states_by_task_id[task.task_id] = self._build_updated_row_state_for_task(
            row_state=updated_row_state,
            task=task,
        )

        self.setRowHeight(row_index, QUEUE_ROW_HEIGHT)
        self._row_presenter.set_task_row_values(
            row_index=row_index, row_state=self._row_states_by_task_id[task.task_id]
        )
        current_row_state = self._row_states_by_task_id.get(task.task_id)

        if current_row_state is not None:
            self._sync_progress_for_row_state(
                row_index=row_index,
                row_state=current_row_state,
            )
        else:
            self._progress_presenter.sync_with_task_status(row_index=row_index, task=task)
        self._quality_presenter.sync_timer()
        self.resize_columns_to_viewport()
        self._sync_empty_hint_visibility()

    def set_platform_icon_path(self, *, task_id: UUID, icon_path: Path) -> None:
        row_index = self._row_by_task_id.get(task_id)
        row_state = self._row_states_by_task_id.get(task_id)

        if row_index is None or row_state is None:
            return

        updated_row_state = row_state.with_platform_icon_path(icon_path=icon_path)
        self._row_states_by_task_id[task_id] = updated_row_state
        self._row_presenter.set_mode_platform_icon(
            row_index=row_index,
            row_state=updated_row_state,
        )

    def _build_updated_row_state_for_task(
        self,
        *,
        row_state: QueueTableRowState,
        task: DownloadTask,
    ) -> QueueTableRowState:
        updated_row_state = row_state.with_task(task=task)

        if task.status is DownloadStatus.RUNNING:
            return updated_row_state.with_download_preparation_running(is_running=False).with_download_prepared(
                is_prepared=True
            )

        if task.status in {
            DownloadStatus.COMPLETED,
            DownloadStatus.FAILED,
            DownloadStatus.CANCELED,
        }:
            return updated_row_state.with_download_preparation_running(is_running=False).with_download_prepared(
                is_prepared=False
            )

        return updated_row_state

    def _sync_progress_for_row_state(
        self,
        *,
        row_index: int,
        row_state: QueueTableRowState,
    ) -> None:
        task = row_state.task

        if task.status is DownloadStatus.PENDING and row_state.is_download_preparation_running:
            self._progress_presenter.prepare_tasks_for_download(
                task_ids=(task.task_id,),
            )
            return

        if task.status is DownloadStatus.PENDING and row_state.is_download_prepared:
            self._progress_presenter.mark_task_prepared(task_id=task.task_id)
            return

        self._progress_presenter.sync_with_task_status(row_index=row_index, task=task)

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

            if previous_row_state.is_metadata_resolution_pending:
                self.mark_quality_resolution_pending(task_id=task.task_id)

            if previous_row_state.is_metadata_resolution_failed:
                self.mark_metadata_resolution_failed(task_id=task.task_id)

            if previous_row_state.is_download_preparation_running:
                self._mark_tasks_preparation_running(task_ids=(task.task_id,))
                self._progress_presenter.prepare_tasks_for_download(
                    task_ids=(task.task_id,),
                )

            if previous_row_state.is_download_prepared:
                self._mark_tasks_prepared_for_download(task_ids=(task.task_id,))
                self._progress_presenter.mark_task_prepared(task_id=task.task_id)

        self.resize_columns_to_viewport()
        self._sync_empty_hint_visibility()

        if len(tasks) == 0:
            QTimer.singleShot(0, self._sync_empty_hint_visibility)

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

    def mark_metadata_resolution_pending(self, *, task_id: UUID) -> None:
        self._quality_presenter.mark_pending(task_id=task_id)
        self._refresh_task_row(task_id=task_id)

    def mark_quality_resolution_pending(self, *, task_id: UUID) -> None:
        self.mark_metadata_resolution_pending(task_id=task_id)

    def clear_metadata_resolution_pending(self, *, task_id: UUID) -> None:
        self._quality_presenter.clear_pending(task_id=task_id)
        self._refresh_task_row(task_id=task_id)

    def clear_quality_resolution_pending(self, *, task_id: UUID) -> None:
        self.clear_metadata_resolution_pending(task_id=task_id)

    def _refresh_task_row(self, *, task_id: UUID) -> None:
        row_index = self._row_by_task_id.get(task_id)
        row_state = self._row_states_by_task_id.get(task_id)

        if row_index is None or row_state is None:
            return

        self._row_presenter.set_task_row_values(row_index=row_index, row_state=row_state)

    def mark_metadata_resolution_failed(self, *, task_id: UUID) -> None:
        self._url_presenter.mark_metadata_resolution_failed(task_id=task_id)

    def prepare_tasks_for_download(self, *, task_ids: tuple[UUID, ...]) -> None:
        self._mark_tasks_preparation_running(task_ids=task_ids)
        self._progress_presenter.prepare_tasks_for_download(task_ids=task_ids)

    def mark_tasks_prepared_for_download(self, *, task_ids: tuple[UUID, ...]) -> None:
        self._mark_tasks_prepared_for_download(task_ids=task_ids)

        for task_id in task_ids:
            self._progress_presenter.mark_task_prepared(task_id=task_id)

    def _mark_tasks_preparation_running(self, *, task_ids: tuple[UUID, ...]) -> None:
        for task_id in task_ids:
            row_state = self._row_states_by_task_id.get(task_id)

            if row_state is None:
                continue

            self._row_states_by_task_id[task_id] = row_state.with_download_preparation_running(
                is_running=True
            ).with_download_prepared(is_prepared=False)

    def _mark_tasks_prepared_for_download(self, *, task_ids: tuple[UUID, ...]) -> None:
        for task_id in task_ids:
            row_state = self._row_states_by_task_id.get(task_id)

            if row_state is None:
                continue

            self._row_states_by_task_id[task_id] = row_state.with_download_preparation_running(
                is_running=False
            ).with_download_prepared(is_prepared=True)

    def set_task_progress(self, progress: DownloadProgress) -> None:
        row_state = self._row_states_by_task_id.get(progress.task_id)

        if row_state is not None:
            self._row_states_by_task_id[progress.task_id] = row_state.with_download_preparation_running(
                is_running=False
            ).with_download_prepared(is_prepared=True)

        self._url_presenter.set_progress(progress=progress)
        self._progress_presenter.set_task_progress(progress=progress)

    def resize_columns_to_viewport(self) -> None:
        resize_download_queue_table_columns_to_viewport(table=self)

    def _handle_viewport_drag_enter(self, *, event: QDragEnterEvent) -> bool:
        if self._accept_supported_url_drag_event(event=event):
            return True

        return super().viewportEvent(event)

    def _handle_viewport_drag_move(self, *, event: QDragMoveEvent) -> bool:
        if self._accept_supported_url_drag_event(event=event):
            return True

        return super().viewportEvent(event)

    def _handle_viewport_drag_leave(self, *, event: QDragLeaveEvent) -> bool:
        self._set_drop_highlight_active(is_active=False)
        event.accept()
        return True

    def _handle_viewport_drop(self, *, event: QDropEvent) -> bool:
        if self._handle_supported_url_drop_event(event=event):
            return True

        return super().viewportEvent(event)

    def _handle_supported_url_drop_event(
        self,
        *,
        event: QDropEvent | None,
    ) -> bool:
        self._set_drop_highlight_active(is_active=False)

        if event is None:
            return False

        dropped_url = extract_first_supported_media_url_from_drop_event(event=event)

        if dropped_url is None:
            return False

        if self._on_url_dropped is not None:
            self._on_url_dropped(dropped_url)

        event.acceptProposedAction()
        return True

    def _accept_supported_url_drag_event(
        self,
        *,
        event: QDragEnterEvent | QDragMoveEvent | None,
    ) -> bool:
        if event is None:
            self._set_drop_highlight_active(is_active=False)
            return False

        if extract_first_supported_media_url_from_drop_event(event=event) is None:
            self._set_drop_highlight_active(is_active=False)
            return False

        self._set_drop_highlight_active(is_active=True)
        event.acceptProposedAction()
        return True

    def _handle_viewport_context_menu(self, *, event: QContextMenuEvent) -> bool:
        clicked_item = self.itemAt(event.pos())

        if clicked_item is None:
            self._clear_current_cell_focus()
            event.accept()
            return True

        prepare_right_click_selection(
            table=self,
            clicked_item=clicked_item,
        )
        selected_task_ids = self.get_selected_task_ids()
        result = show_download_queue_context_menu(
            parent=self,
            global_position=event.globalPos(),
            selected_tasks=self._get_tasks_by_ids(task_ids=selected_task_ids),
            selected_task_ids=selected_task_ids,
            prepared_task_ids=self._get_prepared_task_ids(task_ids=selected_task_ids),
        )

        if result is None:
            event.accept()
            return True

        self._handle_context_menu_result(result=result)
        event.accept()
        return True

    def _handle_context_menu_result(self, *, result: DownloadQueueContextMenuResult) -> None:
        action = result.action
        task_ids = result.task_ids

        if action is DownloadQueueContextAction.COPY:
            self._copy_task_urls_to_clipboard(
                tasks=self._get_tasks_by_ids(task_ids=task_ids),
            )
            return

        if action is DownloadQueueContextAction.DOWNLOAD:
            self._download_tasks(task_ids=task_ids)
            return

        if action is DownloadQueueContextAction.CANCEL and task_ids:
            self._cancel_tasks(task_ids=task_ids)
            return

        if action is DownloadQueueContextAction.REMOVE:
            self._remove_tasks(task_ids=task_ids)

    def _get_selected_tasks(self) -> tuple[DownloadTask, ...]:
        return self._get_tasks_by_ids(task_ids=self.get_selected_task_ids())

    def _get_prepared_task_ids(self, *, task_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
        prepared_task_ids: list[UUID] = []

        for task_id in task_ids:
            row_state = self._row_states_by_task_id.get(task_id)

            if row_state is None:
                continue

            if (
                row_state.is_download_preparation_running
                or row_state.is_download_prepared
                or self._progress_presenter.has_progress_bar(task_id=task_id)
            ):
                prepared_task_ids.append(task_id)

        return tuple(prepared_task_ids)

    def _get_tasks_by_ids(self, *, task_ids: tuple[UUID, ...]) -> tuple[DownloadTask, ...]:
        tasks: list[DownloadTask] = []

        for task_id in task_ids:
            row_state = self._row_states_by_task_id.get(task_id)

            if row_state is not None:
                tasks.append(row_state.task)

        return tuple(tasks)

    def _get_selected_rows(self) -> tuple[int, ...]:
        return get_selected_rows(table=self)

    def _is_row_selected(self, *, row_index: int) -> bool:
        return is_row_selected(table=self, row_index=row_index)

    def _build_empty_hint_label(self) -> QLabel:
        label = QLabel(QUEUE_EMPTY_HINT_TEXT, self)
        label.setObjectName("QueueEmptyHintLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        label.hide()

        return label

    def _build_drop_highlight_overlay(self) -> QueueDropHighlightOverlay:
        return QueueDropHighlightOverlay(parent=cast(QWidget, self.viewport()))

    def _sync_empty_hint_visibility(self) -> None:
        is_empty = self.rowCount() == 0
        self._empty_hint_label.setVisible(is_empty)

        if not is_empty:
            return

        self._reset_empty_queue_scroll_position()
        self._position_empty_hint_label()
        self._empty_hint_label.raise_()

    def _reset_empty_queue_scroll_position(self) -> None:
        if self.rowCount() != 0:
            return

        vertical_scroll_bar = cast(QScrollBar, self.verticalScrollBar())
        horizontal_scroll_bar = cast(QScrollBar, self.horizontalScrollBar())

        vertical_scroll_bar.setValue(0)
        horizontal_scroll_bar.setValue(0)

    def _position_empty_hint_label(self) -> None:
        viewport = cast(QWidget, self.viewport())
        label_rect = build_queue_empty_hint_label_rect(
            viewport_geometry=viewport.geometry(),
        )
        self._empty_hint_label.setGeometry(label_rect)

    def _set_drop_highlight_active(self, *, is_active: bool) -> None:
        self._sync_drop_highlight_geometry()
        self._drop_highlight_overlay.set_active(is_active=is_active)

    def _sync_drop_highlight_geometry(self) -> None:
        self._drop_highlight_overlay.sync_geometry()

    def _sync_overlay_scroll_bar(self) -> None:
        if self._overlay_scroll_bar_controller is not None:
            self._overlay_scroll_bar_controller.sync()

    def _handle_viewport_mouse_press(self, *, event: QMouseEvent) -> bool:
        clicked_position = event.position().toPoint()
        clicked_item = self.itemAt(clicked_position)

        if event.button() == Qt.MouseButton.LeftButton:
            self._reset_left_drag_state()

            if clicked_item is None:
                self._clear_current_cell_focus()
                self.clearFocus()
                event.accept()
                return True

            row_index = clicked_item.row()
            self._left_press_row = row_index
            self._left_press_position = clicked_position
            self._last_drag_y_position = clicked_position.y()
            self.selectRow(row_index)
            self._schedule_long_press_selection(row=row_index)
            event.accept()
            return True

        self._reset_left_drag_state()

        if event.button() != Qt.MouseButton.RightButton:
            return False

        if clicked_item is None:
            self._clear_current_cell_focus()
            event.accept()
            return True

        prepare_right_click_selection(
            table=self,
            clicked_item=clicked_item,
        )
        self._suppress_next_context_menu_event = True
        selected_task_ids = self.get_selected_task_ids()
        result = show_download_queue_context_menu(
            parent=self,
            global_position=event.globalPosition().toPoint(),
            selected_tasks=self._get_tasks_by_ids(task_ids=selected_task_ids),
            selected_task_ids=selected_task_ids,
            prepared_task_ids=self._get_prepared_task_ids(task_ids=selected_task_ids),
        )

        if result is not None:
            self._handle_context_menu_result(result=result)

        event.accept()
        return True

    def _handle_viewport_mouse_move(self, *, event: QMouseEvent) -> bool:
        if self._left_press_row is None:
            return False

        if not event.buttons() & Qt.MouseButton.LeftButton:
            self._reset_left_drag_state()
            return False

        current_position = event.position().toPoint()

        if self._is_long_press_selection_active:
            target_row = self._get_row_for_vertical_drag(y_position=current_position.y())

            if target_row is None:
                return False

            self._select_vertical_row_range(
                anchor_row=self._left_press_row,
                target_row=target_row,
            )
            event.accept()
            return True

        if self._is_long_press_candidate_moved(current_position=current_position):
            self._cancel_long_press_selection()

        self._scroll_vertically_by_drag(current_y_position=current_position.y())
        event.accept()
        return True

    def _handle_viewport_mouse_release(self, *, event: QMouseEvent) -> bool:
        if event.button() != Qt.MouseButton.LeftButton:
            return False

        was_long_press_selection_active = self._is_long_press_selection_active
        self._reset_left_drag_state()

        return was_long_press_selection_active

    def _schedule_long_press_selection(self, *, row: int) -> None:
        self._long_press_generation += 1
        generation = self._long_press_generation

        QTimer.singleShot(
            LONG_PRESS_SELECTION_DELAY_MS,
            lambda: self._activate_long_press_selection(
                row=row,
                generation=generation,
            ),
        )

    def _activate_long_press_selection(self, *, row: int, generation: int) -> None:
        if generation != self._long_press_generation:
            return

        if self._left_press_row != row:
            return

        if self._left_press_position is None:
            return

        self._set_long_press_selection_active(is_active=True)
        self._vertical_row_selection_anchor_row = row
        self._select_vertical_row_range(anchor_row=row, target_row=row)

    def _cancel_long_press_selection(self) -> None:
        self._long_press_generation += 1
        self._set_long_press_selection_active(is_active=False)
        self._vertical_row_selection_anchor_row = None

    def _set_long_press_selection_active(self, *, is_active: bool) -> None:
        if self._is_long_press_selection_active == is_active:
            return

        self._is_long_press_selection_active = is_active
        self.row_selection_mode_changed.emit(is_active)

    def _reset_left_drag_state(self) -> None:
        self._cancel_long_press_selection()
        self._left_press_row = None
        self._left_press_position = None
        self._last_drag_y_position = None

    def _is_long_press_candidate_moved(self, *, current_position: QPoint) -> bool:
        if self._left_press_position is None:
            return True

        delta = current_position - self._left_press_position
        return abs(delta.x()) > LONG_PRESS_MOVE_TOLERANCE_PX or abs(delta.y()) > LONG_PRESS_MOVE_TOLERANCE_PX

    def _scroll_vertically_by_drag(self, *, current_y_position: int) -> None:
        if self._last_drag_y_position is None:
            self._last_drag_y_position = current_y_position
            return

        delta_y = current_y_position - self._last_drag_y_position
        self._last_drag_y_position = current_y_position

        if delta_y == 0:
            return

        vertical_scroll_bar = cast(QScrollBar, self.verticalScrollBar())
        vertical_scroll_bar.setValue(vertical_scroll_bar.value() - delta_y)

        horizontal_scroll_bar = cast(QScrollBar, self.horizontalScrollBar())
        horizontal_scroll_bar.setValue(0)

    def _get_row_for_vertical_drag(self, *, y_position: int) -> int | None:
        if self.rowCount() == 0:
            return None

        row_index = self.rowAt(y_position)

        if row_index >= 0:
            return row_index

        if y_position < 0:
            return 0

        return self.rowCount() - 1

    def _select_vertical_row_range(self, *, anchor_row: int, target_row: int) -> None:
        first_row = max(0, min(anchor_row, target_row))
        last_row = min(self.rowCount() - 1, max(anchor_row, target_row))

        selection_model = self.selectionModel()

        if not isinstance(selection_model, QItemSelectionModel):
            return

        model = cast(QAbstractItemModel, self.model())
        top_left_index = model.index(first_row, 0)
        bottom_right_index = model.index(last_row, max(0, self.columnCount() - 1))
        current_index = model.index(target_row, 0)

        selection = QItemSelection(top_left_index, bottom_right_index)
        selection_model.select(
            selection,
            QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
        )
        selection_model.setCurrentIndex(
            current_index,
            QItemSelectionModel.SelectionFlag.NoUpdate,
        )

    def _download_tasks(self, task_ids: tuple[UUID, ...]) -> None:
        if self._on_download_tasks is not None:
            self._on_download_tasks(task_ids)

    def _cancel_tasks(self, task_ids: tuple[UUID, ...]) -> None:
        if self._on_cancel_tasks is not None:
            self._on_cancel_tasks(task_ids)

    def _remove_tasks(self, task_ids: tuple[UUID, ...]) -> None:
        if self._on_remove_tasks is not None:
            self._on_remove_tasks(task_ids)

    def _remove_selected_tasks_from_keyboard(self) -> None:
        selected_task_ids = self.get_selected_task_ids()

        if not selected_task_ids:
            return

        self._remove_tasks(task_ids=selected_task_ids)

    def _clear_queue_from_keyboard(self) -> None:
        if self.rowCount() == 0:
            return

        if self._on_clear_queue is not None:
            self._on_clear_queue()

    def _copy_selected_urls_to_clipboard(self) -> None:
        selected_tasks = self._get_tasks_by_ids(task_ids=self.get_selected_task_ids())

        if not selected_tasks:
            return

        self._copy_task_urls_to_clipboard(tasks=selected_tasks)

    def _copy_task_urls_to_clipboard(self, *, tasks: tuple[DownloadTask, ...]) -> None:
        self._clipboard_presenter.copy_tasks_to_clipboard(tasks=tasks)

    def _clear_current_cell_focus(self) -> None:
        clear_current_cell_focus(table=self)
