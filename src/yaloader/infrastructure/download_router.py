from __future__ import annotations

from dataclasses import dataclass

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.dto.media_metadata import MediaMetadataProbe
from yaloader.application.dto.prepared_download import PreparedDownload
from yaloader.application.ports.download_preparer import DownloadPreparer
from yaloader.application.ports.downloader import CancellationToken, Downloader, ProgressCallback
from yaloader.application.ports.media_metadata_extractor import MediaMetadataExtractor
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.source_platform import SourcePlatform, detect_source_platform


@dataclass(frozen=True, slots=True)
class RoutedMediaMetadataExtractor:
    vk_audio_extractor: MediaMetadataExtractor
    fallback_extractor: MediaMetadataExtractor

    def extract(self, request: DownloadRequest) -> MediaMetadataProbe:
        if is_vk_audio_source_url(url=request.url):
            return self.vk_audio_extractor.extract(request)

        return self.fallback_extractor.extract(request)


@dataclass(frozen=True, slots=True)
class RoutedDownloadPreparer:
    vk_audio_preparer: DownloadPreparer
    fallback_preparer: DownloadPreparer

    def prepare(
        self,
        task: DownloadTask,
        cancellation_token: CancellationToken | None = None,
    ) -> PreparedDownload:
        if is_vk_audio_source_url(url=task.url.value):
            return self.vk_audio_preparer.prepare(
                task=task,
                cancellation_token=cancellation_token,
            )

        return self.fallback_preparer.prepare(
            task=task,
            cancellation_token=cancellation_token,
        )


@dataclass(frozen=True, slots=True)
class RoutedDownloader:
    vk_audio_downloader: Downloader
    fallback_downloader: Downloader

    def download(
        self,
        task: DownloadTask,
        progress_callback: ProgressCallback | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> DownloadResult:
        if is_vk_audio_source_url(url=task.url.value):
            return self.vk_audio_downloader.download(
                task=task,
                progress_callback=progress_callback,
                cancellation_token=cancellation_token,
            )

        return self.fallback_downloader.download(
            task=task,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token,
        )


def is_vk_audio_source_url(*, url: str) -> bool:
    return detect_source_platform(url=url) is SourcePlatform.VK_AUDIO
