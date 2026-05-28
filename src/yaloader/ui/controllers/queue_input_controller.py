from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality
from yaloader.domain.format_rules import get_download_mode_for_output_format


@dataclass(frozen=True, slots=True)
class QueueInputControllerUpdate:
    status_message: str | None = None
    added_task: DownloadTask | None = None
    metadata_request: DownloadRequest | None = None
    should_clear_url_input: bool = False
    should_focus_url_input: bool = False


class QueueInputController:
    def __init__(self, *, queue_service: DownloadQueueService) -> None:
        self._queue_service = queue_service

    def add_from_input(
        self,
        *,
        url: str,
        target_dir: Path,
        output_format: OutputFormat,
        video_quality: VideoQuality,
    ) -> QueueInputControllerUpdate:
        normalized_url = url.strip()

        if not normalized_url:
            return QueueInputControllerUpdate(
                status_message="Сначала вставьте ссылку",
                should_focus_url_input=True,
            )

        try:
            request = DownloadRequest(
                url=normalized_url,
                target_dir=target_dir,
                mode=get_download_mode_for_output_format(output_format=output_format),
                output_format=output_format,
                video_quality=video_quality,
            )
        except ValidationError as error:
            first_error_message = error.errors()[0]["msg"]
            return QueueInputControllerUpdate(
                status_message=f"Некорректная задача загрузки: {first_error_message}",
                should_focus_url_input=True,
            )

        existing_task = self._queue_service.get_task_by_url(url=request.url)

        if existing_task is not None:
            return QueueInputControllerUpdate(
                status_message="Эта ссылка уже есть в очереди",
                should_focus_url_input=True,
            )

        task = self._queue_service.add_download(request=request)

        return QueueInputControllerUpdate(
            status_message=self._build_success_message(request=request),
            added_task=task,
            metadata_request=request,
            should_clear_url_input=True,
            should_focus_url_input=True,
        )

    def _build_success_message(self, *, request: DownloadRequest) -> str:
        if request.mode is DownloadMode.VIDEO:
            return "Добавлено в очередь. Определяем доступное качество..."

        return f"Добавлено в очередь: {self._queue_service.count()}"
