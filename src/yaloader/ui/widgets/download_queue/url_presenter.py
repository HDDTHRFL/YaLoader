from __future__ import annotations

from typing import cast
from uuid import UUID

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QWidget

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.source_media_kind import SourceMediaKind, detect_source_media_kind
from yaloader.ui.widgets.download_queue.columns import URL_COLUMN_INDEX
from yaloader.ui.widgets.download_queue.delegate import (
    URL_COPY_FEEDBACK_ROLE,
    URL_TITLE_ROLE,
    URL_TITLE_STATE_DEFAULT,
    URL_TITLE_STATE_ERROR,
    URL_TITLE_STATE_ROLE,
)
from yaloader.ui.widgets.download_queue.row_state import QueueTableRowState

METADATA_RESOLUTION_FAILED_TEXT = "Название не удалось определить..."
METADATA_RESOLUTION_PENDING_TEXT = "Checking..."


class DownloadQueueUrlPresenter:
    def __init__(
        self,
        *,
        table: QTableWidget,
        row_by_task_id: dict[UUID, int],
        row_states_by_task_id: dict[UUID, QueueTableRowState],
    ) -> None:
        self._table = table
        self._row_by_task_id = row_by_task_id
        self._row_states_by_task_id = row_states_by_task_id

    def configure_url_item(
        self,
        *,
        row_index: int,
        table_item: QTableWidgetItem,
        task: DownloadTask,
    ) -> None:
        row_state = self._row_states_by_task_id.get(task.task_id)

        if row_state is not None and row_state.is_metadata_resolution_failed:
            self.set_secondary_text(
                row_index=row_index,
                text=METADATA_RESOLUTION_FAILED_TEXT,
                state=URL_TITLE_STATE_ERROR,
                tooltip=f"{task.url.value}\n{METADATA_RESOLUTION_FAILED_TEXT}",
            )
            return

        if row_state is not None and row_state.is_metadata_resolution_pending:
            self.set_secondary_text(
                row_index=row_index,
                text=METADATA_RESOLUTION_PENDING_TEXT,
                state=URL_TITLE_STATE_DEFAULT,
                tooltip=f"{task.url.value}\n{METADATA_RESOLUTION_PENDING_TEXT}",
            )
            return

        normalized_title = self.normalize_task_title(task=task)

        if normalized_title is None:
            table_item.setData(URL_TITLE_ROLE, None)
            table_item.setData(URL_TITLE_STATE_ROLE, URL_TITLE_STATE_DEFAULT)
            table_item.setToolTip(task.url.value)
            return

        self.set_secondary_text(
            row_index=row_index,
            text=normalized_title,
            state=URL_TITLE_STATE_DEFAULT,
            tooltip=f"{task.url.value}\n{normalized_title}",
        )

    def set_progress(self, *, progress: DownloadProgress) -> None:
        row_index = self._row_by_task_id.get(progress.task_id)
        row_state = self._row_states_by_task_id.get(progress.task_id)

        if row_index is None or row_state is None:
            return

        task = row_state.task

        if not task.include_playlist:
            return

        playlist_title = self._build_running_playlist_title(
            task=task,
            progress=progress,
        )

        if playlist_title is None:
            return

        self.set_secondary_text(
            row_index=row_index,
            text=playlist_title,
            state=URL_TITLE_STATE_DEFAULT,
            tooltip=f"{task.url.value}\n{playlist_title}",
        )

    def mark_metadata_resolution_failed(self, *, task_id: UUID) -> None:
        row_index = self._row_by_task_id.get(task_id)
        row_state = self._row_states_by_task_id.get(task_id)

        if row_index is None or row_state is None:
            return

        self._row_states_by_task_id[task_id] = row_state.with_metadata_resolution_failed(is_failed=True)
        self.set_secondary_text(
            row_index=row_index,
            text=METADATA_RESOLUTION_FAILED_TEXT,
            state=URL_TITLE_STATE_ERROR,
            tooltip=f"{row_state.task.url.value}\n{METADATA_RESOLUTION_FAILED_TEXT}",
        )

    def clear_metadata_resolution_failed_if_title_exists(self, *, task: DownloadTask) -> None:
        if self.normalize_task_title(task=task) is None:
            return

        row_state = self._row_states_by_task_id.get(task.task_id)

        if row_state is None:
            return

        self._row_states_by_task_id[task.task_id] = row_state.with_metadata_resolution_failed(is_failed=False)

    def set_copy_feedback(self, *, task_id: UUID, text: str | None) -> None:
        row_index = self._row_by_task_id.get(task_id)

        if row_index is None:
            return

        table_item = self._table.item(row_index, URL_COLUMN_INDEX)

        if table_item is None:
            return

        table_item.setData(URL_COPY_FEEDBACK_ROLE, text)
        self._refresh_viewport()

    def set_secondary_text(
        self,
        *,
        row_index: int,
        text: str,
        state: str,
        tooltip: str,
    ) -> None:
        table_item = self._table.item(row_index, URL_COLUMN_INDEX)

        if table_item is None:
            return

        table_item.setData(URL_TITLE_ROLE, text)
        table_item.setData(URL_TITLE_STATE_ROLE, state)
        table_item.setToolTip(tooltip)

        self._refresh_viewport()

    def normalize_task_title(self, *, task: DownloadTask) -> str | None:
        source_kind = detect_source_media_kind(
            url=task.url.value,
            include_playlist=task.include_playlist,
        )
        normalized_title = self._normalize_title_value(title=task.title)

        if source_kind is SourceMediaKind.PLAYLIST:
            return self._build_pending_playlist_title(
                title=normalized_title,
                playlist_count=task.playlist_count,
            )

        if source_kind is SourceMediaKind.SHORTS:
            if normalized_title is None:
                return "[SHORTS]"

            return f"[SHORTS] · {normalized_title}"

        return normalized_title

    def _build_pending_playlist_title(
        self,
        *,
        title: str | None,
        playlist_count: int | None,
    ) -> str:
        if playlist_count is not None and title is not None:
            return f"[PLAYLIST] · {playlist_count} · {title}"

        if playlist_count is not None:
            return f"[PLAYLIST] · {playlist_count}"

        if title is not None:
            return f"[PLAYLIST] · {title}"

        return "[PLAYLIST]"

    def _build_running_playlist_title(
        self,
        *,
        task: DownloadTask,
        progress: DownloadProgress,
    ) -> str | None:
        current_title = self._normalize_title_value(title=progress.current_title)

        if current_title is None:
            return None

        playlist_index = progress.playlist_index
        playlist_count = progress.playlist_count or task.playlist_count

        if playlist_index is not None and playlist_count is not None:
            return f"[PLAYLIST] · {playlist_index}/{playlist_count} · {current_title}"

        if playlist_index is not None:
            return f"[PLAYLIST] · {playlist_index} · {current_title}"

        return f"[PLAYLIST] · {current_title}"

    def _normalize_title_value(self, *, title: str | None) -> str | None:
        if title is None:
            return None

        normalized_title = title.strip()

        if not normalized_title:
            return None

        return normalized_title

    def _refresh_viewport(self) -> None:
        viewport = cast(QWidget, self._table.viewport())
        viewport.update()
