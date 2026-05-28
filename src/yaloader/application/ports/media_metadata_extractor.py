from __future__ import annotations

from typing import Protocol

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.media_metadata import MediaMetadataProbe


class MediaMetadataExtractor(Protocol):
    def extract(self, request: DownloadRequest) -> MediaMetadataProbe: ...
