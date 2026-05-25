from __future__ import annotations

from typing import Protocol

from yaloader.application.dto.download_result import DownloadResult
from yaloader.domain.entities.download_task import DownloadTask


class Downloader(Protocol):
    def download(self, task: DownloadTask) -> DownloadResult: ...
