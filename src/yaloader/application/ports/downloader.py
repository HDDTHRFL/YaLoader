from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.application.dto.download_result import DownloadResult
from yaloader.domain.entities.download_task import DownloadTask

ProgressCallback = Callable[[DownloadProgress], None]


class CancellationToken(Protocol):
    @property
    def is_cancel_requested(self) -> bool: ...


class Downloader(Protocol):
    def download(
        self,
        task: DownloadTask,
        progress_callback: ProgressCallback | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> DownloadResult: ...
