from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.services.download_history_service import DownloadHistoryService
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.domain.entities.download_task import DownloadTask


@dataclass(frozen=True, slots=True)
class HistoryControllerUpdate:
    status_message: str | None = None
    records: tuple[DownloadHistoryRecord, ...] | None = None
    added_task: DownloadTask | None = None
    metadata_request: DownloadRequest | None = None
    should_clear_download_history_flags: bool = False


class HistoryController:
    def __init__(
        self,
        *,
        history_service: DownloadHistoryService,
        queue_service: DownloadQueueService,
    ) -> None:
        self._history_service = history_service
        self._queue_service = queue_service

    def load(self) -> HistoryControllerUpdate:
        return HistoryControllerUpdate(records=self._history_service.load())

    def clear(self) -> HistoryControllerUpdate:
        removed_count = self._history_service.clear()

        if removed_count == 0:
            return HistoryControllerUpdate(
                status_message="История уже пустая",
                records=(),
                should_clear_download_history_flags=True,
            )

        return HistoryControllerUpdate(
            status_message=f"История очищена. Удалено записей: {removed_count}",
            records=(),
            should_clear_download_history_flags=True,
        )

    def remove_record(self, *, record: DownloadHistoryRecord) -> HistoryControllerUpdate:
        removed_count = self._history_service.remove_by_task_id(task_id=record.task_id)

        if removed_count == 0:
            return HistoryControllerUpdate(
                status_message="Запись истории уже удалена",
                records=self._history_service.load(),
            )

        return HistoryControllerUpdate(
            status_message="Запись удалена из истории",
            records=self._history_service.load(),
        )

    def add_record_to_queue(self, *, record: DownloadHistoryRecord) -> HistoryControllerUpdate:
        try:
            record.target_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            return HistoryControllerUpdate(
                status_message=f"Не удалось подготовить папку загрузки: {error}",
            )

        try:
            request = DownloadRequest(
                url=record.url,
                target_dir=record.target_dir,
                mode=record.mode,
                output_format=record.output_format,
                video_quality=record.video_quality,
                include_playlist=record.include_playlist,
                download_speed_limit_bytes_per_second=(record.download_speed_limit_bytes_per_second),
            )
        except ValidationError as error:
            first_error_message = error.errors()[0]["msg"]
            return HistoryControllerUpdate(
                status_message=f"Не удалось добавить из истории: {first_error_message}",
            )

        existing_task = self._queue_service.get_task_by_url(url=request.url)

        if existing_task is not None:
            return HistoryControllerUpdate(status_message="Эта ссылка уже есть в очереди")

        task = self._queue_service.add_download(request=request)
        restored_task = self._queue_service.apply_metadata(
            task_id=task.task_id,
            title=record.title,
            video_quality=record.video_quality,
            playlist_count=record.playlist_count,
        )

        if restored_task is not None:
            task = restored_task

        return HistoryControllerUpdate(
            status_message=self._build_add_to_queue_success_message(request=request),
            added_task=task,
            metadata_request=None if request.include_playlist else request,
        )

    def _build_add_to_queue_success_message(self, *, request: DownloadRequest) -> str:
        if request.include_playlist:
            return "Плейлист из истории добавлен в очередь загрузок"

        return "Задача из истории добавлена в очередь загрузок"
