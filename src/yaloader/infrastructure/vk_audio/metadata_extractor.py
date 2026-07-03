from __future__ import annotations

from dataclasses import dataclass

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.media_metadata import MediaMetadataProbe
from yaloader.infrastructure.vk_audio.client import VkAudioClient, format_track_title


@dataclass(frozen=True, slots=True)
class VkAudioMetadataExtractor:
    client: VkAudioClient

    def extract(self, request: DownloadRequest) -> MediaMetadataProbe:
        media = self.client.resolve_direct_media(url=request.url)

        return MediaMetadataProbe(
            url=request.url,
            title=format_track_title(
                artist=media.artist,
                title=media.title,
            ),
            duration_seconds=media.duration_seconds,
        )
