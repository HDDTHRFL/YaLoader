from __future__ import annotations

from uuid import UUID

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QProgressBar, QTableWidget, QTableWidgetItem

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.domain.download_speed_limit import format_bytes_per_second
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus
from yaloader.ui.widgets.download_queue.columns import STATUS_PROGRESS_COLUMN_INDEX

PREPARATION_ANIMATION_INTERVAL_MS = 420
PREPARING_DOWNLOAD_TOOLTIP = "Подготавливаем загрузку"
PREPARED_DOWNLOAD_TOOLTIP = "Загрузка подготовлена и ожидает очереди"
PREPARED_DOWNLOAD_TEXT = "prepared"
PREPARING_DOWNLOAD_TEXT_STATES = (
    "running.",
    "running..",
    "running...",
)

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
        self._preparing_task_ids: set[UUID] = set()
        self._preparation_step_index = 0
        self._preparation_timer = QTimer(table)
        self._configure_preparation_timer()

    def prepare_tasks_for_download(self, *, task_ids: tuple[UUID, ...]) -> None:
        for task_id in task_ids:
            row_index = self._row_by_task_id.get(task_id)

            if row_index is None:
                continue

            self._preparing_task_ids.add(task_id)
            self._set_preparation_text(row_index=row_index)

        self._sync_preparation_timer()

    def mark_task_prepared(self, *, task_id: UUID) -> None:
        self._preparing_task_ids.discard(task_id)
        self._sync_preparation_timer()

        row_index = self._row_by_task_id.get(task_id)

        if row_index is None:
            return

        progress_bar = self._ensure_progress_bar(row_index=row_index)
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat(PREPARED_DOWNLOAD_TEXT)
        progress_bar.setToolTip(PREPARED_DOWNLOAD_TOOLTIP)

    def clear_task_download_state(self, *, task_id: UUID) -> None:
        self._preparing_task_ids.discard(task_id)
        self._sync_preparation_timer()

    def has_progress_bar(self, *, task_id: UUID) -> bool:
        row_index = self._row_by_task_id.get(task_id)

        if row_index is None:
            return False

        return isinstance(
            self._table.cellWidget(row_index, STATUS_PROGRESS_COLUMN_INDEX),
            QProgressBar,
        )

    def set_task_progress(self, progress: DownloadProgress) -> None:
        self._preparing_task_ids.discard(progress.task_id)
        self._sync_preparation_timer()

        row_index = self._row_by_task_id.get(progress.task_id)

        if row_index is None:
            return

        progress_bar = self._ensure_progress_bar(row_index=row_index)
        progress_bar.setTextVisible(True)

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
        self.clear_task_download_state(task_id=task.task_id)

        if task.status is DownloadStatus.RUNNING:
            progress_bar = self._ensure_progress_bar(row_index=row_index)
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setTextVisible(False)
            progress_bar.setFormat("")
            progress_bar.setToolTip(PREPARED_DOWNLOAD_TOOLTIP)
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

    def _configure_preparation_timer(self) -> None:
        self._preparation_timer.setInterval(PREPARATION_ANIMATION_INTERVAL_MS)
        self._preparation_timer.timeout.connect(self._handle_preparation_timer_timeout)

    def _handle_preparation_timer_timeout(self) -> None:
        self._preparation_step_index = (self._preparation_step_index + 1) % len(PREPARING_DOWNLOAD_TEXT_STATES)
        stale_task_ids: list[UUID] = []

        for task_id in tuple(self._preparing_task_ids):
            row_index = self._row_by_task_id.get(task_id)

            if row_index is None:
                stale_task_ids.append(task_id)
                continue

            self._set_preparation_text(row_index=row_index)

        for task_id in stale_task_ids:
            self._preparing_task_ids.discard(task_id)

        self._sync_preparation_timer()

    def _sync_preparation_timer(self) -> None:
        if self._preparing_task_ids:
            if not self._preparation_timer.isActive():
                self._preparation_timer.start()
            return

        if self._preparation_timer.isActive():
            self._preparation_timer.stop()

    def _set_preparation_text(self, *, row_index: int) -> None:
        self.set_text(
            row_index=row_index,
            text=PREPARING_DOWNLOAD_TEXT_STATES[self._preparation_step_index],
        )
        table_item = self._table.item(row_index, STATUS_PROGRESS_COLUMN_INDEX)

        if table_item is not None:
            table_item.setToolTip(PREPARING_DOWNLOAD_TOOLTIP)

    def _build_progress_bar_text(self, *, progress: DownloadProgress) -> str:
        if progress.status_text == PROCESSING_STATUS_TEXT:
            return PROCESSING_STATUS_TEXT

        progress_text = f"{progress.progress_bar_value}%"

        if progress.speed_bytes_per_second is None:
            return progress_text

        return f"{progress_text} · {format_bytes_per_second(bytes_per_second=progress.speed_bytes_per_second)}"

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
