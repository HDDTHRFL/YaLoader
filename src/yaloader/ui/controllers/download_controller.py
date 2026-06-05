from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, SimpleQueue
from time import sleep
from typing import Final
from uuid import UUID

from loguru import logger

from yaloader.application.dto.cancellation import DownloadCancellationToken
from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.dto.prepared_download import PreparedDownload
from yaloader.application.ports.download_preparer import DownloadPreparer
from yaloader.application.ports.downloader import Downloader, ProgressCallback
from yaloader.application.services.download_history_service import DownloadHistoryService
from yaloader.application.services.download_queue_service import (
    DownloadQueueService,
    is_downloadable,
)
from yaloader.application.services.prepared_download_cache import PreparedDownloadCache
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus

DOWNLOAD_WORKERS_COUNT = 1
PREPARATION_WORKERS_COUNT = 3
PREPARATION_WAIT_POLL_SECONDS = 0.05

HISTORY_RECORD_STATUSES: Final[frozenset[DownloadStatus]] = frozenset(
    {
        DownloadStatus.COMPLETED,
        DownloadStatus.FAILED,
        DownloadStatus.CANCELED,
    }
)

CANCELABLE_TASK_STATUSES: Final[frozenset[DownloadStatus]] = frozenset(
    {
        DownloadStatus.PENDING,
        DownloadStatus.RUNNING,
    }
)


@dataclass(frozen=True, slots=True)
class DownloadPreparationResult:
    task_id: UUID
    prepared_download: PreparedDownload | None = None
    error_message: str | None = None
    is_canceled: bool = False


@dataclass(frozen=True, slots=True)
class DownloadControllerUpdate:
    status_message: str | None = None
    updated_tasks: tuple[DownloadTask, ...] = ()
    progress_events: tuple[DownloadProgress, ...] = ()
    prepared_task_ids: tuple[UUID, ...] = ()
    completed_preparation_task_ids: tuple[UUID, ...] = ()
    tasks_snapshot: tuple[DownloadTask, ...] | None = None
    should_reload_history: bool = False


class DownloadController:
    def __init__(
        self,
        *,
        queue_service: DownloadQueueService,
        history_service: DownloadHistoryService,
        downloader: Downloader,
        download_preparer: DownloadPreparer | None = None,
        prepared_download_cache: PreparedDownloadCache | None = None,
    ) -> None:
        self._queue_service = queue_service
        self._history_service = history_service
        self._downloader = downloader
        self._download_preparer = download_preparer
        self._prepared_download_cache = prepared_download_cache

        self._queued_task_ids: list[UUID] = []
        self._recorded_history_task_ids: set[UUID] = set()
        self._progress_events: SimpleQueue[DownloadProgress] = SimpleQueue()

        self._download_executor = ThreadPoolExecutor(
            max_workers=DOWNLOAD_WORKERS_COUNT,
            thread_name_prefix="yaloader-download",
        )
        self._preparation_executor = ThreadPoolExecutor(
            max_workers=PREPARATION_WORKERS_COUNT,
            thread_name_prefix="yaloader-prepare",
        )
        self._active_download_future: Future[DownloadResult] | None = None
        self._active_download_task_id: UUID | None = None
        self._active_cancellation_token: DownloadCancellationToken | None = None
        self._preparation_futures_by_task_id: dict[UUID, Future[DownloadPreparationResult]] = {}
        self._preparation_tokens_by_task_id: dict[UUID, DownloadCancellationToken] = {}

    @property
    def is_active(self) -> bool:
        return self._active_download_future is not None

    @property
    def active_task_id(self) -> UUID | None:
        return self._active_download_task_id

    def shutdown(self) -> None:
        if self._active_cancellation_token is not None:
            self._active_cancellation_token.request_cancel()

        self._cancel_preparation_tokens(task_ids=tuple(self._preparation_tokens_by_task_id))
        self._download_executor.shutdown(wait=False, cancel_futures=True)
        self._preparation_executor.shutdown(wait=False, cancel_futures=True)

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
            self._prepare_tasks_for_download(task_ids=queued_task_ids),
            self._start_next_queued_download(),
        )

    def start_tasks(self, *, task_ids: tuple[UUID, ...]) -> DownloadControllerUpdate:
        downloadable_task_ids = self._collect_downloadable_task_ids(task_ids=task_ids)

        if not downloadable_task_ids:
            return DownloadControllerUpdate(
                status_message="Среди выбранных задач нет доступных для загрузки"
            )

        if self.is_active:
            queued_task_ids = tuple(
                task_id
                for task_id in downloadable_task_ids
                if task_id not in self._queued_task_ids and task_id != self._active_download_task_id
            )

            if not queued_task_ids:
                return DownloadControllerUpdate(
                    status_message="Выбранные задачи уже ожидают скачивания"
                )

            self._queued_task_ids.extend(queued_task_ids)

            return merge_download_updates(
                self._prepare_tasks_for_download(task_ids=queued_task_ids),
                DownloadControllerUpdate(
                    status_message=f"Добавлено в текущую очередь: {len(queued_task_ids)}",
                ),
            )

        queued_task_ids = downloadable_task_ids
        self._queued_task_ids = list(queued_task_ids)

        return merge_download_updates(
            self._prepare_tasks_for_download(task_ids=queued_task_ids),
            self._start_next_queued_download(),
        )

    def _collect_downloadable_task_ids(self, *, task_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
        downloadable_task_ids: list[UUID] = []
        seen_task_ids: set[UUID] = set()

        for task_id in task_ids:
            if task_id in seen_task_ids:
                continue

            seen_task_ids.add(task_id)
            task = self._queue_service.get_task(task_id=task_id)

            if task is not None and is_downloadable(task):
                downloadable_task_ids.append(task.task_id)

        return tuple(downloadable_task_ids)

    def cancel_active_download(self) -> DownloadControllerUpdate:
        if self._active_cancellation_token is None or self._active_download_task_id is None:
            return DownloadControllerUpdate(status_message="Нет активной загрузки для отмены")

        task_ids_to_cancel = self._build_prepared_task_ids_for_cancel()
        self._queued_task_ids.clear()
        self._active_cancellation_token.request_cancel()
        self._cancel_preparation_tokens(task_ids=task_ids_to_cancel)

        updated_tasks: list[DownloadTask] = []
        should_reload_history = False

        for task_id in task_ids_to_cancel:
            self._remove_prepared_download_from_cache(task_id=task_id)
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
        return self.cancel_tasks_download(task_ids=(task_id,))

    def cancel_tasks_download(self, *, task_ids: tuple[UUID, ...]) -> DownloadControllerUpdate:
        unique_task_ids = tuple(dict.fromkeys(task_ids))

        if not unique_task_ids:
            return DownloadControllerUpdate(status_message="Выберите задачи для отмены")

        task_id_set = set(unique_task_ids)
        is_active_task_cancel_requested = (
            self._active_download_task_id is not None
            and self._active_download_task_id in task_id_set
        )

        if is_active_task_cancel_requested and self._active_cancellation_token is not None:
            self._active_cancellation_token.request_cancel()

        self._cancel_preparation_tokens(task_ids=unique_task_ids)
        self._queued_task_ids = [
            queued_task_id
            for queued_task_id in self._queued_task_ids
            if queued_task_id not in task_id_set
        ]

        updated_tasks: list[DownloadTask] = []
        should_reload_history = False

        for task_id in unique_task_ids:
            self._remove_prepared_download_from_cache(task_id=task_id)
            task = self._queue_service.get_task(task_id=task_id)

            if task is None or task.status not in CANCELABLE_TASK_STATUSES:
                continue

            canceled_task = self._queue_service.update_status(
                task_id=task.task_id,
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

        if not updated_tasks:
            return DownloadControllerUpdate(
                status_message="Среди выбранных задач нет активных или ожидающих загрузок"
            )

        if is_active_task_cancel_requested:
            status_message = "Отмена выбранной загрузки... Частичные файлы будут удалены"
        elif len(updated_tasks) == 1:
            status_message = "Выбранная задача отменена"
        else:
            status_message = f"Отменено выбранных задач: {len(updated_tasks)}"

        return DownloadControllerUpdate(
            status_message=status_message,
            updated_tasks=tuple(updated_tasks),
            should_reload_history=should_reload_history,
        )

    def remove_tasks_from_queue(self, *, task_ids: tuple[UUID, ...]) -> DownloadControllerUpdate:
        if self._active_download_task_id in task_ids:
            return DownloadControllerUpdate(
                status_message="Нельзя удалить задачу, которая сейчас выполняется"
            )

        self._cancel_preparation_tokens(task_ids=task_ids)

        removed_count = 0

        for task_id in task_ids:
            self._remove_prepared_download_from_cache(task_id=task_id)
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

        self._cancel_preparation_tokens(task_ids=tuple(self._preparation_tokens_by_task_id))
        self._clear_prepared_download_cache()
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
        preparation_update = self._drain_preparation_results()

        if self._active_download_future is None:
            return merge_download_updates(
                preparation_update,
                DownloadControllerUpdate(progress_events=progress_events),
            )

        if not self._active_download_future.done():
            return merge_download_updates(
                preparation_update,
                DownloadControllerUpdate(progress_events=progress_events),
            )

        future = self._active_download_future
        self._active_download_future = None
        self._active_download_task_id = None
        self._active_cancellation_token = None

        try:
            result = future.result()
        except Exception as error:
            return merge_download_updates(
                preparation_update,
                DownloadControllerUpdate(
                    status_message=f"Ошибка загрузки: {error}",
                    progress_events=progress_events,
                ),
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
                preparation_update,
                result_update,
                self._start_next_queued_download(),
            )

        if updated_task is not None and updated_task.status is DownloadStatus.CANCELED:
            return merge_download_updates(
                preparation_update,
                result_update,
                DownloadControllerUpdate(
                    status_message="Загрузка отменена. Частичные файлы удалены"
                ),
            )

        if result.status is DownloadStatus.COMPLETED:
            return merge_download_updates(
                preparation_update,
                result_update,
                DownloadControllerUpdate(status_message="Очередь загрузок завершена"),
            )

        return merge_download_updates(
            preparation_update,
            result_update,
            DownloadControllerUpdate(
                status_message=f"Загрузка завершилась ошибкой: {result.error_message}"
            ),
        )

    def _prepare_tasks_for_download(
        self, *, task_ids: tuple[UUID, ...]
    ) -> DownloadControllerUpdate:
        prepared_task_ids: list[UUID] = []

        for task_id in task_ids:
            task = self._queue_service.get_task(task_id=task_id)

            if task is None or not is_downloadable(task):
                continue

            if self._start_preparation_for_task(task=task):
                prepared_task_ids.append(task.task_id)

        return DownloadControllerUpdate(prepared_task_ids=tuple(prepared_task_ids))

    def _start_preparation_for_task(self, *, task: DownloadTask) -> bool:
        if self._download_preparer is None:
            return True

        if self._is_prepared_download_cached(task_id=task.task_id):
            return True

        if task.task_id in self._preparation_futures_by_task_id:
            return True

        cancellation_token = DownloadCancellationToken()
        future = self._preparation_executor.submit(
            self._prepare_task_worker,
            task=task,
            cancellation_token=cancellation_token,
        )
        self._preparation_futures_by_task_id[task.task_id] = future
        self._preparation_tokens_by_task_id[task.task_id] = cancellation_token

        return True

    def _prepare_task_worker(
        self,
        *,
        task: DownloadTask,
        cancellation_token: DownloadCancellationToken,
    ) -> DownloadPreparationResult:
        download_preparer = self._download_preparer

        if download_preparer is None:
            return DownloadPreparationResult(task_id=task.task_id, is_canceled=True)

        try:
            prepared_download = download_preparer.prepare(
                task=task,
                cancellation_token=cancellation_token,
            )

            if cancellation_token.is_cancel_requested:
                return DownloadPreparationResult(task_id=task.task_id, is_canceled=True)

            if self._prepared_download_cache is not None:
                self._prepared_download_cache.save(prepared_download=prepared_download)

            return DownloadPreparationResult(
                task_id=task.task_id,
                prepared_download=prepared_download,
            )
        except Exception as error:
            if cancellation_token.is_cancel_requested:
                return DownloadPreparationResult(task_id=task.task_id, is_canceled=True)

            logger.opt(exception=error).warning(
                "Download preparation failed. task_id={} url={} error={}",
                task.task_id,
                task.url.value,
                error,
            )
            return DownloadPreparationResult(
                task_id=task.task_id,
                error_message=str(error),
            )

    def _drain_preparation_results(self) -> DownloadControllerUpdate:
        updated_tasks: list[DownloadTask] = []
        completed_preparation_task_ids: list[UUID] = []
        status_message: str | None = None

        for task_id, future in tuple(self._preparation_futures_by_task_id.items()):
            if not future.done():
                continue

            self._preparation_futures_by_task_id.pop(task_id, None)
            self._preparation_tokens_by_task_id.pop(task_id, None)

            try:
                result = future.result()
            except Exception as error:
                logger.opt(exception=error).warning(
                    "Download preparation future failed unexpectedly. task_id={}",
                    task_id,
                )
                completed_preparation_task_ids.append(task_id)
                status_message = "Подготовка загрузки не удалась. yt-dlp попробует скачать напрямую"
                continue

            if result.is_canceled:
                continue

            completed_preparation_task_ids.append(result.task_id)

            if result.prepared_download is None:
                status_message = "Подготовка загрузки не удалась. yt-dlp попробует скачать напрямую"
                continue

            updated_task = self._apply_prepared_download(result.prepared_download)

            if updated_task is not None:
                updated_tasks.append(updated_task)

        return DownloadControllerUpdate(
            status_message=status_message,
            updated_tasks=tuple(updated_tasks),
            completed_preparation_task_ids=tuple(completed_preparation_task_ids),
        )

    def _apply_prepared_download(
        self,
        prepared_download: PreparedDownload,
    ) -> DownloadTask | None:
        current_task = self._queue_service.get_task(task_id=prepared_download.task_id)

        if current_task is None:
            return None

        if current_task.status in {
            DownloadStatus.RUNNING,
            DownloadStatus.COMPLETED,
            DownloadStatus.CANCELED,
        }:
            return None

        return self._queue_service.apply_metadata(
            task_id=current_task.task_id,
            title=prepared_download.title,
            video_quality=current_task.video_quality,
            playlist_count=prepared_download.playlist_count,
        )

    def _download_task_worker(
        self,
        *,
        task: DownloadTask,
        progress_callback: ProgressCallback,
        cancellation_token: DownloadCancellationToken,
    ) -> DownloadResult:
        preparation_cancel_result = self._wait_for_task_preparation(
            task=task,
            cancellation_token=cancellation_token,
        )

        if preparation_cancel_result is not None:
            return preparation_cancel_result

        return self._downloader.download(
            task=task,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token,
        )

    def _wait_for_task_preparation(
        self,
        *,
        task: DownloadTask,
        cancellation_token: DownloadCancellationToken,
    ) -> DownloadResult | None:
        future = self._preparation_futures_by_task_id.get(task.task_id)

        if future is None:
            return None

        while not future.done():
            if cancellation_token.is_cancel_requested:
                return DownloadResult.canceled(task_id=task.task_id)

            sleep(PREPARATION_WAIT_POLL_SECONDS)

        try:
            result = future.result()
        except Exception as error:
            logger.opt(exception=error).warning(
                "Download preparation wait failed unexpectedly. task_id={}",
                task.task_id,
            )
            return None

        if result.is_canceled or cancellation_token.is_cancel_requested:
            return DownloadResult.canceled(task_id=task.task_id)

        return None

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
                self._download_task_worker,
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

    def _cancel_preparation_tokens(self, *, task_ids: tuple[UUID, ...]) -> None:
        for task_id in task_ids:
            cancellation_token = self._preparation_tokens_by_task_id.get(task_id)

            if cancellation_token is not None:
                cancellation_token.request_cancel()

    def _is_prepared_download_cached(self, *, task_id: UUID) -> bool:
        if self._prepared_download_cache is None:
            return False

        return self._prepared_download_cache.contains(task_id=task_id)

    def _remove_prepared_download_from_cache(self, *, task_id: UUID) -> None:
        if self._prepared_download_cache is None:
            return

        self._prepared_download_cache.remove(task_id=task_id)

    def _clear_prepared_download_cache(self) -> None:
        if self._prepared_download_cache is None:
            return

        self._prepared_download_cache.clear()


def merge_download_updates(
    *updates: DownloadControllerUpdate,
) -> DownloadControllerUpdate:
    status_message: str | None = None
    updated_tasks: list[DownloadTask] = []
    progress_events: list[DownloadProgress] = []
    prepared_task_ids: list[UUID] = []
    completed_preparation_task_ids: list[UUID] = []
    tasks_snapshot: tuple[DownloadTask, ...] | None = None
    should_reload_history = False

    for update in updates:
        if update.status_message is not None:
            status_message = update.status_message

        updated_tasks.extend(update.updated_tasks)
        progress_events.extend(update.progress_events)
        prepared_task_ids.extend(update.prepared_task_ids)
        completed_preparation_task_ids.extend(update.completed_preparation_task_ids)
        should_reload_history = should_reload_history or update.should_reload_history

        if update.tasks_snapshot is not None:
            tasks_snapshot = update.tasks_snapshot

    return DownloadControllerUpdate(
        status_message=status_message,
        updated_tasks=tuple(updated_tasks),
        progress_events=tuple(progress_events),
        prepared_task_ids=tuple(prepared_task_ids),
        completed_preparation_task_ids=tuple(completed_preparation_task_ids),
        tasks_snapshot=tasks_snapshot,
        should_reload_history=should_reload_history,
    )
