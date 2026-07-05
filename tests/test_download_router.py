from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.dto.media_metadata import MediaMetadataProbe
from yaloader.application.dto.prepared_download import PreparedDownload
from yaloader.application.ports.downloader import CancellationToken, ProgressCallback
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.domain.value_objects.media_url import MediaUrl
from yaloader.infrastructure.download_router import (
    RoutedDownloader,
    RoutedDownloadPreparer,
    RoutedMediaMetadataExtractor,
)
from yaloader.infrastructure.vk_audio.client import VkAudioProbeError

VK_AUDIO_URL = "https://vk.com/audio-2001247451_41247451"
VK_AUDIO_ACCESS_KEY_URL = "https://vk.com/audio-2001247451_41247451_c98d766105ddecb1b3"
YOUTUBE_URL = "https://www.youtube.com/watch?v=test"


@dataclass(slots=True)
class FakeMetadataExtractor:
    title: str
    calls: int = 0

    def extract(self, request: DownloadRequest) -> MediaMetadataProbe:
        self.calls += 1

        return MediaMetadataProbe(
            url=request.url,
            title=self.title,
        )


@dataclass(slots=True)
class FailingVkAudioMetadataExtractor:
    calls: int = 0

    def extract(self, request: DownloadRequest) -> MediaMetadataProbe:
        self.calls += 1
        raise VkAudioProbeError("VK asks for authorization")


@dataclass(slots=True)
class FakeDownloadPreparer:
    calls: int = 0

    def prepare(
        self,
        task: DownloadTask,
        cancellation_token: CancellationToken | None = None,
    ) -> PreparedDownload:
        self.calls += 1

        return PreparedDownload(
            task_id=task.task_id,
            url=task.url.value,
            title=task.title,
        )


@dataclass(slots=True)
class FakeDownloader:
    calls: int = 0

    def download(
        self,
        task: DownloadTask,
        progress_callback: ProgressCallback | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> DownloadResult:
        self.calls += 1

        return DownloadResult.completed(task_id=task.task_id)


def test_vk_audio_metadata_probe_keeps_unresolved_title_when_vk_requires_login(tmp_path: Path) -> None:
    request = create_audio_request(url=VK_AUDIO_URL, target_dir=tmp_path)
    vk_extractor = FailingVkAudioMetadataExtractor()
    fallback_extractor = FakeMetadataExtractor(title="fallback")
    router = RoutedMediaMetadataExtractor(
        vk_audio_extractor=vk_extractor,
        fallback_extractor=fallback_extractor,
    )

    metadata = router.extract(request)

    assert metadata.url == VK_AUDIO_URL
    assert metadata.title is None
    assert vk_extractor.calls == 1
    assert fallback_extractor.calls == 0


def test_vk_audio_metadata_probe_does_not_show_access_key_in_fallback_title(tmp_path: Path) -> None:
    request = create_audio_request(url=VK_AUDIO_ACCESS_KEY_URL, target_dir=tmp_path)
    vk_extractor = FailingVkAudioMetadataExtractor()
    fallback_extractor = FakeMetadataExtractor(title="fallback")
    router = RoutedMediaMetadataExtractor(
        vk_audio_extractor=vk_extractor,
        fallback_extractor=fallback_extractor,
    )

    metadata = router.extract(request)

    assert metadata.url == VK_AUDIO_ACCESS_KEY_URL
    assert metadata.title is None
    assert vk_extractor.calls == 1
    assert fallback_extractor.calls == 0


def test_regular_url_metadata_uses_ytdlp_fallback_extractor(tmp_path: Path) -> None:
    request = create_video_request(url=YOUTUBE_URL, target_dir=tmp_path)
    vk_extractor = FailingVkAudioMetadataExtractor()
    fallback_extractor = FakeMetadataExtractor(title="fallback")
    router = RoutedMediaMetadataExtractor(
        vk_audio_extractor=vk_extractor,
        fallback_extractor=fallback_extractor,
    )

    metadata = router.extract(request)

    assert metadata.title == "fallback"
    assert vk_extractor.calls == 0
    assert fallback_extractor.calls == 1


def test_vk_audio_preparer_does_not_fall_back_to_ytdlp(tmp_path: Path) -> None:
    task = create_audio_task(url=VK_AUDIO_URL, target_dir=tmp_path)
    vk_preparer = FakeDownloadPreparer()
    fallback_preparer = FakeDownloadPreparer()
    router = RoutedDownloadPreparer(
        vk_audio_preparer=vk_preparer,
        fallback_preparer=fallback_preparer,
    )

    router.prepare(task=task)

    assert vk_preparer.calls == 1
    assert fallback_preparer.calls == 0


def test_vk_audio_downloader_does_not_fall_back_to_ytdlp(tmp_path: Path) -> None:
    task = create_audio_task(url=VK_AUDIO_URL, target_dir=tmp_path)
    vk_downloader = FakeDownloader()
    fallback_downloader = FakeDownloader()
    router = RoutedDownloader(
        vk_audio_downloader=vk_downloader,
        fallback_downloader=fallback_downloader,
    )

    result = router.download(task=task)

    assert result.status is DownloadStatus.COMPLETED
    assert vk_downloader.calls == 1
    assert fallback_downloader.calls == 0


def create_audio_request(*, url: str, target_dir: Path) -> DownloadRequest:
    return DownloadRequest(
        url=url,
        target_dir=target_dir,
        mode=DownloadMode.AUDIO,
        output_format=OutputFormat.MP3,
        video_quality=VideoQuality.BEST,
    )


def create_video_request(*, url: str, target_dir: Path) -> DownloadRequest:
    return DownloadRequest(
        url=url,
        target_dir=target_dir,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )


def create_audio_task(*, url: str, target_dir: Path) -> DownloadTask:
    return DownloadTask.create(
        url=MediaUrl(value=url),
        target_dir=target_dir,
        mode=DownloadMode.AUDIO,
        output_format=OutputFormat.MP3,
        video_quality=VideoQuality.BEST,
        include_playlist=False,
    )
