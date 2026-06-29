from __future__ import annotations

from uuid import UUID

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QClipboard, QGuiApplication

from yaloader.domain.entities.download_task import DownloadTask
from yaloader.ui.widgets.download_queue.row_state import QueueTableRowState
from yaloader.ui.widgets.download_queue.url_presenter import DownloadQueueUrlPresenter

COPY_FEEDBACK_DURATION_MS = 1000
COPY_FEEDBACK_TEXT = "Ссылка скопирована..."


class DownloadQueueClipboardPresenter:
    def __init__(
        self,
        *,
        url_presenter: DownloadQueueUrlPresenter,
        row_states_by_task_id: dict[UUID, QueueTableRowState],
    ) -> None:
        self._url_presenter = url_presenter
        self._row_states_by_task_id = row_states_by_task_id
        self._copy_feedback_generation = 0

    def copy_tasks_to_clipboard(self, *, tasks: tuple[DownloadTask, ...]) -> None:
        if not tasks:
            return

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
            row_state = self._row_states_by_task_id.get(task_id)

            if row_state is None:
                continue

            self._row_states_by_task_id[task_id] = row_state.with_copy_feedback_generation(generation=generation)
            self._url_presenter.set_copy_feedback(task_id=task_id, text=COPY_FEEDBACK_TEXT)

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
            row_state = self._row_states_by_task_id.get(task_id)

            if row_state is None or row_state.copy_feedback_generation != generation:
                continue

            self._row_states_by_task_id[task_id] = row_state.with_copy_feedback_generation(generation=None)
            self._url_presenter.set_copy_feedback(task_id=task_id, text=None)
