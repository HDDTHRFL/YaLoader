from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.ports.downloader import CancellationToken, ProgressCallback
from yaloader.application.services.prepared_download_cache import PreparedDownloadCache
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.infrastructure.vk_audio.client import VkAudioClient, VkAudioDirectMedia
from yaloader.infrastructure.vk_audio.download_preparer import (
    VkAudioDownloadCancelledError,
    build_vk_audio_media_from_task_url_and_raw_info,
    raise_if_cancel_requested,
    validate_vk_audio_task,
)


@dataclass(frozen=True, slots=True)
class VkAudioDownloader:
    client: VkAudioClient
    prepared_download_cache: PreparedDownloadCache | None = None

    def download(
        self,
        task: DownloadTask,
        progress_callback: ProgressCallback | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> DownloadResult:
        try:
            raise_if_cancel_requested(cancellation_token=cancellation_token)
            validate_vk_audio_task(task=task)

            if progress_callback is not None:
                progress_callback(DownloadProgress.started(task_id=task.task_id))

            media = self._resolve_media(task=task)
            raise_if_cancel_requested(cancellation_token=cancellation_token)

            if progress_callback is not None:
                progress_callback(DownloadProgress.processing(task_id=task.task_id))

            output_path = self.client.download_media(
                media=media,
                download_dir=task.target_dir,
                output_format=task.output_format.value,
            )
            raise_if_cancel_requested(cancellation_token=cancellation_token)

            if progress_callback is not None:
                progress_callback(DownloadProgress.completed(task_id=task.task_id))

            logger.info(
                "VK Audio download completed. task_id={} output_path={}",
                task.task_id,
                output_path,
            )
            return DownloadResult.completed(
                task_id=task.task_id,
                output_path=output_path,
            )
        except VkAudioDownloadCancelledError:
            if progress_callback is not None:
                progress_callback(DownloadProgress.canceled(task_id=task.task_id))

            return DownloadResult.canceled(task_id=task.task_id)
        except Exception as error:
            error_message = str(error)

            logger.warning(
                "VK Audio download failed. task_id={} error_type={} error={}",
                task.task_id,
                type(error).__name__,
                error_message,
            )

            if progress_callback is not None:
                progress_callback(DownloadProgress.failed(task_id=task.task_id))

            return DownloadResult.failed(
                task_id=task.task_id,
                error_message=error_message,
            )

    def _resolve_media(self, *, task: DownloadTask) -> VkAudioDirectMedia:
        cached_media = self._load_cached_media(task=task)

        if cached_media is not None:
            return cached_media

        return self.client.resolve_direct_media(url=task.url.value)

    def _load_cached_media(self, *, task: DownloadTask) -> VkAudioDirectMedia | None:
        if self.prepared_download_cache is None:
            return None

        prepared_download = self.prepared_download_cache.get(task_id=task.task_id)

        if prepared_download is None:
            return None

        if prepared_download.url != task.url.value:
            return None

        return build_vk_audio_media_from_task_url_and_raw_info(
            task=task,
            raw_info=prepared_download.raw_info,
        )


def detect_created_vk_audio_output_path(
    *,
    download_dir: Path,
    existing_files: frozenset[Path],
) -> Path | None:
    created_files = tuple(
        file_path for file_path in download_dir.iterdir() if file_path.is_file() and file_path not in existing_files
    )

    if not created_files:
        return None

    return max(created_files, key=lambda path: path.stat().st_mtime)
