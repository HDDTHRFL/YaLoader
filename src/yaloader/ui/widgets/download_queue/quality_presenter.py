from __future__ import annotations

from uuid import UUID

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem

from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus
from yaloader.ui.widgets.download_queue.columns import QUALITY_COLUMN_INDEX
from yaloader.ui.widgets.download_queue.row_state import QueueTableRowState

QUALITY_RESOLUTION_ANIMATION_INTERVAL_MS = 420
QUALITY_RESOLUTION_TOOLTIP = "Определяем доступное качество"
QUALITY_RESOLUTION_TEXT_STATES = (
    "Checking.",
    "Checking..",
    "Checking...",
)


class DownloadQueueQualityPresenter:
    def __init__(
        self,
        *,
        table: QTableWidget,
        row_by_task_id: dict[UUID, int],
        row_states_by_task_id: dict[UUID, QueueTableRowState],
        parent: QObject,
    ) -> None:
        self._table = table
        self._row_by_task_id = row_by_task_id
        self._row_states_by_task_id = row_states_by_task_id
        self._step_index = 0
        self._timer = QTimer(parent)

        self._configure_timer()

    def mark_pending(self, *, task_id: UUID) -> None:
        row_index = self._row_by_task_id.get(task_id)
        row_state = self._row_states_by_task_id.get(task_id)

        if row_index is None or row_state is None:
            return

        if row_state.task.status is not DownloadStatus.PENDING:
            return

        self._row_states_by_task_id[task_id] = row_state.with_quality_resolution_pending(
            is_pending=True
        )
        self.set_cell_text(
            row_index=row_index,
            text=self.build_pending_text(),
            tooltip=QUALITY_RESOLUTION_TOOLTIP,
        )
        self.sync_timer()

    def clear_pending(self, *, task_id: UUID) -> None:
        row_index = self._row_by_task_id.get(task_id)
        row_state = self._row_states_by_task_id.get(task_id)

        if row_index is None or row_state is None:
            return

        was_pending = row_state.is_quality_resolution_pending
        self._row_states_by_task_id[task_id] = row_state.with_quality_resolution_pending(
            is_pending=False
        )
        self.sync_timer()

        if not was_pending:
            return

        self.set_cell_text(
            row_index=row_index,
            text=row_state.task.video_quality.value,
            tooltip=row_state.task.video_quality.value,
        )

    def clear_pending_if_task_is_not_pending(self, *, task: DownloadTask) -> None:
        row_state = self._row_states_by_task_id.get(task.task_id)

        if row_state is None:
            return

        if task.status is DownloadStatus.PENDING:
            return

        self._row_states_by_task_id[task.task_id] = row_state.with_quality_resolution_pending(
            is_pending=False
        )

    def build_cell_text(self, *, task: DownloadTask) -> str:
        if self.is_pending(task_id=task.task_id):
            return self.build_pending_text()

        return task.video_quality.value

    def build_cell_tooltip(self, *, task: DownloadTask) -> str:
        if self.is_pending(task_id=task.task_id):
            return QUALITY_RESOLUTION_TOOLTIP

        return task.video_quality.value

    def build_pending_text(self) -> str:
        return QUALITY_RESOLUTION_TEXT_STATES[self._step_index]

    def is_pending(self, *, task_id: UUID) -> bool:
        row_state = self._row_states_by_task_id.get(task_id)

        if row_state is None:
            return False

        return row_state.is_quality_resolution_pending

    def sync_timer(self) -> None:
        if self._get_pending_task_ids():
            if not self._timer.isActive():
                self._timer.start()
            return

        if self._timer.isActive():
            self._timer.stop()

    def set_cell_text(self, *, row_index: int, text: str, tooltip: str) -> None:
        table_item = self._table.item(row_index, QUALITY_COLUMN_INDEX)

        if table_item is None:
            table_item = QTableWidgetItem(text)
            self._table.setItem(row_index, QUALITY_COLUMN_INDEX, table_item)
        else:
            table_item.setText(text)

        table_item.setToolTip(tooltip)

    def _configure_timer(self) -> None:
        self._timer.setInterval(QUALITY_RESOLUTION_ANIMATION_INTERVAL_MS)
        self._timer.timeout.connect(self._advance_animation)

    def _advance_animation(self) -> None:
        pending_task_ids = self._get_pending_task_ids()

        if not pending_task_ids:
            self.sync_timer()
            return

        self._step_index = (self._step_index + 1) % len(QUALITY_RESOLUTION_TEXT_STATES)
        text = self.build_pending_text()

        for task_id in pending_task_ids:
            row_index = self._row_by_task_id.get(task_id)

            if row_index is None:
                self._clear_stale_pending_state(task_id=task_id)
                continue

            self.set_cell_text(
                row_index=row_index,
                text=text,
                tooltip=QUALITY_RESOLUTION_TOOLTIP,
            )

        self.sync_timer()

    def _get_pending_task_ids(self) -> tuple[UUID, ...]:
        return tuple(
            row_state.task.task_id
            for row_state in self._row_states_by_task_id.values()
            if row_state.is_quality_resolution_pending
        )

    def _clear_stale_pending_state(self, *, task_id: UUID) -> None:
        row_state = self._row_states_by_task_id.get(task_id)

        if row_state is None:
            return

        self._row_states_by_task_id[task_id] = row_state.with_quality_resolution_pending(
            is_pending=False
        )
