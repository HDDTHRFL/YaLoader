from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from queue import Empty, SimpleQueue
from uuid import UUID

from loguru import logger

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.media_metadata import MediaMetadata
from yaloader.application.services.media_metadata_service import MediaMetadataService

METADATA_WORKERS_COUNT = 3


@dataclass(frozen=True, slots=True)
class MediaMetadataResolutionResult:
    task_id: UUID
    metadata: MediaMetadata | None = None
    error_message: str | None = None


class MediaMetadataController:
    def __init__(self, service: MediaMetadataService) -> None:
        self._service = service
        self._events: SimpleQueue[MediaMetadataResolutionResult] = SimpleQueue()
        self._executor = ThreadPoolExecutor(
            max_workers=METADATA_WORKERS_COUNT,
            thread_name_prefix="yaloader-metadata",
        )

    def start_resolution(
        self,
        *,
        task_id: UUID,
        request: DownloadRequest,
    ) -> bool:
        self._executor.submit(
            self._resolve_worker,
            task_id=task_id,
            request=request,
        )
        return True

    def drain_results(self) -> tuple[MediaMetadataResolutionResult, ...]:
        results: list[MediaMetadataResolutionResult] = []

        while True:
            try:
                results.append(self._events.get_nowait())
            except Empty:
                return tuple(results)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _resolve_worker(
        self,
        *,
        task_id: UUID,
        request: DownloadRequest,
    ) -> None:
        try:
            metadata = self._service.resolve(request=request)
        except Exception as error:
            logger.warning(
                "Failed to resolve media metadata. task_id={} url={} error_type={} error={}",
                task_id,
                request.url,
                type(error).__name__,
                error,
            )
            self._events.put(
                MediaMetadataResolutionResult(
                    task_id=task_id,
                    error_message=str(error),
                )
            )
            return

        self._events.put(
            MediaMetadataResolutionResult(
                task_id=task_id,
                metadata=metadata,
            )
        )
