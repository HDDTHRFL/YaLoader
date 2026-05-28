from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, SimpleQueue
from typing import Final
from uuid import UUID

from loguru import logger

from yaloader.application.dto.cancellation import DownloadCancellationToken
from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.ports.downloader import Downloader
from yaloader.application.services.download_history_service import DownloadHistoryService
from yaloader.application.services.download_queue_service import (
    DownloadQueueService,
    is_downloadable,
)
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus

DOWNLOAD_WORKERS_COUNT = 1

HISTORY_RECORD_STATUSES: Final[frozenset[DownloadStatus]] = frozenset(
    {
        DownloadStatus.COMPLETED,
        DownloadStatus.FAILED,
        DownloadStatus.CANCELED,
    }
)


@dataclass(frozen=True, slots=True)
class DownloadControllerUpdate:
    status_message: str | None = None
    updated_tasks: tuple[DownloadTask, ...] = ()
    progress_events: tuple[DownloadProgress, ...] = ()
    prepared_task_ids: tuple[UUID, ...] = ()
    tasks_snapshot: tuple[DownloadTask, ...] | None = None
    should_reload_history: bool = False


class DownloadController:
    def __init__(
        self,
        *,
        queue_service: DownloadQueueService,
        history_service: DownloadHistoryService,
        downloader: Downloader,
    ) -> None:
        self._queue_service = queue_service
        self._history_service = history_service
        self._downloader = downloader

        self._queued_task_ids: list[UUID] = []
        self._recorded_history_task_ids: set[UUID] = set()
        self._progress_events: SimpleQueue[DownloadProgress] = SimpleQueue()

        self._download_executor = ThreadPoolExecutor(
            max_workers=DOWNLOAD_WORKERS_COUNT,
            thread_name_prefix="yaloader-download",
        )
        self._active_download_future: Future[DownloadResult] | None = None
        self._active_download_task_id: UUID | None = None
        self._active_cancellation_token: DownloadCancellationToken | None = None

    @property
    def is_active(self) -> bool:
        return self._active_download_future is not None

    @property
    def active_task_id(self) -> UUID | None:
        return self._active_download_task_id

    def shutdown(self) -> None:
        if self._active_cancellation_token is not None:
            self._active_cancellation_token.request_cancel()

        self._download_executor.shutdown(wait=False, cancel_futures=True)

    def clear_recorded_history_flags(self) -> None:
        self._recorded_history_task_ids.clear()

    def start_downloadable_queue(self) -> DownloadControllerUpdate:
        if self.is_active:
            return DownloadControllerUpdate(status_message="Сейчас уже выполняется загрузка")

        downloadable_tasks = self._queue_service.list_downloadable_tasks()

        if not downloadable_tasks:
            return DownloadControllerUpdate(status_message="В очереди нет задач для загрузки")

        queued_task_ids = tuple(task.task_id for task in downloadable_tasks)
        self._queued_task_ids = list(queued_task_ids)

        return merge_download_updates(
            DownloadControllerUpdate(prepared_task_ids=queued_task_ids),
            self._start_next_queued_download(),
        )

    def start_tasks(self, *, task_ids: tuple[UUID, ...]) -> DownloadControllerUpdate:
        if self.is_active:
            return DownloadControllerUpdate(status_message="Сейчас уже выполняется загрузка")

        downloadable_task_ids: list[UUID] = []

        for task_id in task_ids:
            task = self._queue_service.get_task(task_id=task_id)

            if task is not None and is_downloadable(task):
                downloadable_task_ids.append(task.task_id)

        if not downloadable_task_ids:
            return DownloadControllerUpdate(
                status_message="Среди выбранных задач нет доступных для загрузки"
            )

        queued_task_ids = tuple(downloadable_task_ids)
        self._queued_task_ids = list(queued_task_ids)

        return merge_download_updates(
            DownloadControllerUpdate(prepared_task_ids=queued_task_ids),
            self._start_next_queued_download(),
        )

    def cancel_active_download(self) -> DownloadControllerUpdate:
        if self._active_cancellation_token is None or self._active_download_task_id is None:
            return DownloadControllerUpdate(status_message="Нет активной загрузки для отмены")

        task_ids_to_cancel = self._build_prepared_task_ids_for_cancel()
        self._queued_task_ids.clear()
        self._active_cancellation_token.request_cancel()

        updated_tasks: list[DownloadTask] = []
        should_reload_history = False

        for task_id in task_ids_to_cancel:
            canceled_task = self._queue_service.update_status(
                task_id=task_id,
                status=DownloadStatus.CANCELED,
                error_message="Загрузка отменена пользователем.",
            )

            if canceled_task is None:
                continue

            updated_tasks.append(canceled_task)
            should_reload_history = (
                self._record_download_history(task=canceled_task, output_path=None)
                or should_reload_history
            )

        return DownloadControllerUpdate(
            status_message="Отмена загрузки... Частичные файлы будут удалены",
            updated_tasks=tuple(updated_tasks),
            should_reload_history=should_reload_history,
        )

    def cancel_task_download(self, *, task_id: UUID) -> DownloadControllerUpdate:
        if self._active_download_task_id != task_id:
            return DownloadControllerUpdate(
                status_message="Отменить можно только активную загрузку"
            )

        return self.cancel_active_download()

    def remove_tasks_from_queue(self, *, task_ids: tuple[UUID, ...]) -> DownloadControllerUpdate:
        if self._active_download_task_id in task_ids:
            return DownloadControllerUpdate(
                status_message="Нельзя удалить задачу, которая сейчас выполняется"
            )

        removed_count = 0

        for task_id in task_ids:
            removed_task = self._queue_service.remove_task(task_id=task_id)

            if removed_task is not None:
                removed_count += 1

        self._queued_task_ids = [
            queued_task_id
            for queued_task_id in self._queued_task_ids
            if queued_task_id not in task_ids
        ]

        if removed_count == 0:
            return DownloadControllerUpdate(
                status_message="Выбранные задачи не найдены",
                tasks_snapshot=self._queue_service.list_tasks(),
            )

        return DownloadControllerUpdate(
            status_message=f"Удалено из очереди: {removed_count}",
            tasks_snapshot=self._queue_service.list_tasks(),
        )

    def clear_queue(self) -> DownloadControllerUpdate:
        if self.is_active:
            return DownloadControllerUpdate(
                status_message="Нельзя очистить очередь во время загрузки"
            )

        removed_count = self._queue_service.clear_tasks()
        self._queued_task_ids.clear()

        if removed_count == 0:
            return DownloadControllerUpdate(
                status_message="Очередь уже пустая",
                tasks_snapshot=(),
            )

        return DownloadControllerUpdate(
            status_message=f"Очередь очищена. Удалено задач: {removed_count}",
            tasks_snapshot=(),
        )

    def poll(self) -> DownloadControllerUpdate:
        progress_events = self._drain_progress_events()

        if self._active_download_future is None:
            return DownloadControllerUpdate(progress_events=progress_events)

        if not self._active_download_future.done():
            return DownloadControllerUpdate(progress_events=progress_events)

        future = self._active_download_future
        self._active_download_future = None
        self._active_download_task_id = None
        self._active_cancellation_token = None

        try:
            result = future.result()
        except Exception as error:
            return DownloadControllerUpdate(
                status_message=f"Ошибка загрузки: {error}",
                progress_events=progress_events,
            )

        progress_events = (*progress_events, *self._drain_progress_events())
        updated_task = self._apply_download_result(result=result)
        updated_tasks = (updated_task,) if updated_task is not None else ()
        should_reload_history = False

        if updated_task is not None:
            should_reload_history = self._record_download_history(
                task=updated_task,
                output_path=result.output_path,
            )

        result_update = DownloadControllerUpdate(
            updated_tasks=updated_tasks,
            progress_events=progress_events,
            should_reload_history=should_reload_history,
        )

        if self._queued_task_ids:
            return merge_download_updates(
                result_update,
                self._start_next_queued_download(),
            )

        if updated_task is not None and updated_task.status is DownloadStatus.CANCELED:
            return merge_download_updates(
                result_update,
                DownloadControllerUpdate(
                    status_message="Загрузка отменена. Частичные файлы удалены"
                ),
            )

        if result.status is DownloadStatus.COMPLETED:
            return merge_download_updates(
                result_update,
                DownloadControllerUpdate(status_message="Очередь загрузок завершена"),
            )

        return merge_download_updates(
            result_update,
            DownloadControllerUpdate(
                status_message=f"Загрузка завершилась ошибкой: {result.error_message}"
            ),
        )

    def _start_next_queued_download(self) -> DownloadControllerUpdate:
        if self.is_active:
            return DownloadControllerUpdate()

        while self._queued_task_ids:
            task_id = self._queued_task_ids.pop(0)
            task = self._queue_service.get_task(task_id=task_id)

            if task is None or not is_downloadable(task):
                continue

            running_task = self._queue_service.update_status(
                task_id=task.task_id,
                status=DownloadStatus.RUNNING,
            )

            if running_task is None:
                continue

            self._active_download_task_id = running_task.task_id
            self._active_cancellation_token = DownloadCancellationToken()
            self._active_download_future = self._download_executor.submit(
                self._downloader.download,
                task=running_task,
                progress_callback=self._handle_download_progress,
                cancellation_token=self._active_cancellation_token,
            )

            return DownloadControllerUpdate(
                status_message=f"Загрузка запущена: {running_task.url.value}",
                updated_tasks=(running_task,),
                progress_events=(DownloadProgress.started(task_id=running_task.task_id),),
            )

        return DownloadControllerUpdate(status_message="Очередь загрузок завершена")

    def _build_prepared_task_ids_for_cancel(self) -> tuple[UUID, ...]:
        task_ids: list[UUID] = []
        seen_task_ids: set[UUID] = set()

        if self._active_download_task_id is not None:
            task_ids.append(self._active_download_task_id)
            seen_task_ids.add(self._active_download_task_id)

        for task_id in self._queued_task_ids:
            if task_id in seen_task_ids:
                continue

            task_ids.append(task_id)
            seen_task_ids.add(task_id)

        return tuple(task_ids)

    def _handle_download_progress(self, progress: DownloadProgress) -> None:
        self._progress_events.put(progress)

    def _drain_progress_events(self) -> tuple[DownloadProgress, ...]:
        progress_events: list[DownloadProgress] = []

        while True:
            try:
                progress = self._progress_events.get_nowait()
            except Empty:
                return tuple(progress_events)

            task = self._queue_service.get_task(task_id=progress.task_id)

            if task is not None and task.status is DownloadStatus.CANCELED:
                continue

            progress_events.append(progress)

    def _apply_download_result(self, *, result: DownloadResult) -> DownloadTask | None:
        current_task = self._queue_service.get_task(task_id=result.task_id)

        if current_task is not None and current_task.status is DownloadStatus.CANCELED:
            return current_task

        return self._queue_service.apply_result(result=result)

    def _record_download_history(
        self,
        *,
        task: DownloadTask,
        output_path: Path | None,
    ) -> bool:
        if task.task_id in self._recorded_history_task_ids:
            return False

        if task.status not in HISTORY_RECORD_STATUSES:
            return False

        record = DownloadHistoryRecord.create_from_task(
            task=task,
            output_path=output_path,
        )

        try:
            self._history_service.append(record=record)
        except OSError as error:
            logger.warning(
                "Failed to save download history. task_id={} error={}",
                task.task_id,
                error,
            )
            return False

        self._recorded_history_task_ids.add(task.task_id)
        return True


def merge_download_updates(
    *updates: DownloadControllerUpdate,
) -> DownloadControllerUpdate:
    status_message: str | None = None
    updated_tasks: list[DownloadTask] = []
    progress_events: list[DownloadProgress] = []
    prepared_task_ids: list[UUID] = []
    tasks_snapshot: tuple[DownloadTask, ...] | None = None
    should_reload_history = False

    for update in updates:
        if update.status_message is not None:
            status_message = update.status_message

        updated_tasks.extend(update.updated_tasks)
        progress_events.extend(update.progress_events)
        prepared_task_ids.extend(update.prepared_task_ids)
        should_reload_history = should_reload_history or update.should_reload_history

        if update.tasks_snapshot is not None:
            tasks_snapshot = update.tasks_snapshot

    return DownloadControllerUpdate(
        status_message=status_message,
        updated_tasks=tuple(updated_tasks),
        progress_events=tuple(progress_events),
        prepared_task_ids=tuple(prepared_task_ids),
        tasks_snapshot=tasks_snapshot,
        should_reload_history=should_reload_history,
    )
