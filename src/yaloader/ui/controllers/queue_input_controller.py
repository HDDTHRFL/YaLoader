from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.domain.download_speed_limit import format_download_speed_limit_label
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality
from yaloader.domain.format_rules import get_download_mode_for_output_format
from yaloader.domain.source_download_defaults import resolve_output_format_for_source_url
from yaloader.domain.source_playlist_policy import should_include_playlist_for_url
from yaloader.domain.vk_audio_url import (
    VK_AUDIO_PUBLIC_CATALOG_UNSUPPORTED_STATUS_MESSAGE,
    is_unsupported_vk_audio_public_catalog_url,
)


@dataclass(frozen=True, slots=True)
class QueueInputControllerUpdate:
    status_message: str | None = None
    added_task: DownloadTask | None = None
    metadata_request: DownloadRequest | None = None
    should_clear_url_input: bool = False
    should_focus_url_input: bool = False
    is_warning_status: bool = False


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
        separate_audio_video_enabled: bool = False,
        separate_audio_format: OutputFormat = OutputFormat.MP3,
        download_speed_limit_bytes_per_second: int | None = None,
    ) -> QueueInputControllerUpdate:
        normalized_url = url.strip()

        if not normalized_url:
            return QueueInputControllerUpdate(
                status_message="Сначала вставьте ссылку",
                should_focus_url_input=True,
            )

        if is_unsupported_vk_audio_public_catalog_url(url=normalized_url):
            return QueueInputControllerUpdate(
                status_message=VK_AUDIO_PUBLIC_CATALOG_UNSUPPORTED_STATUS_MESSAGE,
                should_focus_url_input=True,
                is_warning_status=True,
            )

        include_playlist = should_include_playlist_for_url(url=normalized_url)
        resolved_output_format = resolve_output_format_for_source_url(
            url=normalized_url,
            selected_output_format=output_format,
        )

        try:
            resolved_mode = get_download_mode_for_output_format(
                output_format=resolved_output_format,
            )
            request = DownloadRequest(
                url=normalized_url,
                target_dir=target_dir,
                mode=resolved_mode,
                output_format=resolved_output_format,
                video_quality=video_quality,
                include_playlist=include_playlist,
                separate_audio_video_enabled=(separate_audio_video_enabled and resolved_mode is DownloadMode.VIDEO),
                separate_audio_format=separate_audio_format,
                download_speed_limit_bytes_per_second=download_speed_limit_bytes_per_second,
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
        if request.include_playlist:
            return append_download_speed_limit_status_suffix(
                message="Плейлист добавлен в очередь загрузок",
                download_speed_limit_bytes_per_second=(request.download_speed_limit_bytes_per_second),
            )

        if request.mode is DownloadMode.VIDEO:
            return append_download_speed_limit_status_suffix(
                message="Добавлено в очередь. Определяем доступное качество...",
                download_speed_limit_bytes_per_second=(request.download_speed_limit_bytes_per_second),
            )

        return append_download_speed_limit_status_suffix(
            message=f"Добавлено в очередь: {self._queue_service.count()}",
            download_speed_limit_bytes_per_second=request.download_speed_limit_bytes_per_second,
        )


def append_download_speed_limit_status_suffix(
    *,
    message: str,
    download_speed_limit_bytes_per_second: int | None,
) -> str:
    if download_speed_limit_bytes_per_second is None:
        return message

    speed_limit_label = format_download_speed_limit_label(
        bytes_per_second=download_speed_limit_bytes_per_second,
    )

    return f"{message} Лимит скорости: {speed_limit_label}"
