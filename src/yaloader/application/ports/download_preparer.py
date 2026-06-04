from __future__ import annotations

from typing import Protocol

from yaloader.application.dto.prepared_download import PreparedDownload
from yaloader.application.ports.downloader import CancellationToken
from yaloader.domain.entities.download_task import DownloadTask


class DownloadPreparer(Protocol):
    def prepare(
        self,
        task: DownloadTask,
        cancellation_token: CancellationToken | None = None,
    ) -> PreparedDownload: ...
