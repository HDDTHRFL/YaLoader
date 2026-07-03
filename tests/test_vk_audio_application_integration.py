from __future__ import annotations

from pathlib import Path

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.media_metadata import MediaMetadataProbe
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.application.services.prepared_download_cache import PreparedDownloadCache
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.infrastructure.download_router import (
    RoutedDownloader,
    RoutedDownloadPreparer,
    RoutedMediaMetadataExtractor,
)
from yaloader.infrastructure.vk_audio.client import VkAudioDirectMedia, VkAudioId
from yaloader.infrastructure.vk_audio.download_preparer import (
    VkAudioDownloadPreparer,
    is_vk_audio_raw_info,
)
from yaloader.infrastructure.vk_audio.downloader import VkAudioDownloader

VK_AUDIO_URL = "https://vk.com/audio133993362_456242612_cb6b8410a741a6993a"


class FakeVkAudioClient:
    def __init__(self) -> None:
        self.resolved_urls: list[str] = []
        self.downloaded_media: list[VkAudioDirectMedia] = []

    def resolve_direct_media(self, *, url: str) -> VkAudioDirectMedia:
        self.resolved_urls.append(url)

        return VkAudioDirectMedia(
            audio_id=VkAudioId(owner_id="133993362", audio_id="456242612", access_key="cb6b8410a741a6993a"),
            direct_url="https://cs9-3v4.vkuseraudio.net/s/v1/ac/example/index.m3u8?token=value",
            title="Death Note",
            artist="Polyphia feat. Ichika",
            duration_seconds=220,
        )

    def download_media(
        self,
        *,
        media: VkAudioDirectMedia,
        download_dir: Path,
        output_format: str | None = None,
    ) -> Path:
        self.downloaded_media.append(media)
        extension = output_format or "mp3"
        output_path = download_dir / f"Polyphia feat. Ichika - Death Note.{extension}"
        output_path.write_text("audio", encoding="utf-8")

        return output_path


class FakeMetadataExtractor:
    def __init__(self, title: str) -> None:
        self.title = title
        self.calls = 0

    def extract(self, request: DownloadRequest) -> MediaMetadataProbe:
        self.calls += 1

        return MediaMetadataProbe(
            url=request.url,
            title=self.title,
        )


class FakeDownloadPreparer:
    def __init__(self, title: str) -> None:
        self.title = title
        self.calls = 0

    def prepare(self, task, cancellation_token=None):
        self.calls += 1

        return task


class FakeDownloader:
    def __init__(self) -> None:
        self.calls = 0

    def download(self, task, progress_callback=None, cancellation_token=None):
        self.calls += 1

        return DownloadStatus.COMPLETED


def build_vk_audio_task(*, target_dir: Path):
    request = DownloadRequest(
        url=VK_AUDIO_URL,
        target_dir=target_dir,
        mode=DownloadMode.AUDIO,
        output_format=OutputFormat.MP3,
        video_quality=VideoQuality.BEST,
    )
    queue_service = DownloadQueueService()

    return queue_service.add_download(request=request)


def test_vk_audio_preparer_resolves_media_and_builds_prepared_download(tmp_path: Path) -> None:
    fake_client = FakeVkAudioClient()
    task = build_vk_audio_task(target_dir=tmp_path)
    preparer = VkAudioDownloadPreparer(client=fake_client)

    prepared_download = preparer.prepare(task=task)

    assert fake_client.resolved_urls == [VK_AUDIO_URL]
    assert prepared_download.title == "Polyphia feat. Ichika - Death Note"
    assert prepared_download.duration_seconds == 220
    assert is_vk_audio_raw_info(raw_info=prepared_download.raw_info)


def test_vk_audio_downloader_uses_cached_prepared_media(tmp_path: Path) -> None:
    fake_client = FakeVkAudioClient()
    task = build_vk_audio_task(target_dir=tmp_path)
    cache = PreparedDownloadCache()
    preparer = VkAudioDownloadPreparer(client=fake_client)
    prepared_download = preparer.prepare(task=task)
    fake_client.resolved_urls.clear()
    cache.save(prepared_download=prepared_download)

    downloader = VkAudioDownloader(
        client=fake_client,
        prepared_download_cache=cache,
    )

    progress_events: list[DownloadProgress] = []
    result = downloader.download(task=task, progress_callback=progress_events.append)

    assert result.status is DownloadStatus.COMPLETED
    assert result.output_path == tmp_path / "Polyphia feat. Ichika - Death Note.mp3"
    assert result.output_path.is_file()
    assert fake_client.resolved_urls == []
    assert len(fake_client.downloaded_media) == 1
    assert [event.status_text for event in progress_events] == ["Ожидание", "Обработка", "Готово"]


def test_routed_metadata_extractor_uses_vk_audio_extractor_for_vk_audio_url(tmp_path: Path) -> None:
    request = DownloadRequest(
        url=VK_AUDIO_URL,
        target_dir=tmp_path,
        mode=DownloadMode.AUDIO,
        output_format=OutputFormat.MP3,
        video_quality=VideoQuality.BEST,
    )
    vk_extractor = FakeMetadataExtractor(title="vk")
    fallback_extractor = FakeMetadataExtractor(title="fallback")
    router = RoutedMediaMetadataExtractor(
        vk_audio_extractor=vk_extractor,
        fallback_extractor=fallback_extractor,
    )

    metadata = router.extract(request)

    assert metadata.title == "vk"
    assert vk_extractor.calls == 1
    assert fallback_extractor.calls == 0


def test_routed_metadata_extractor_uses_fallback_for_regular_url(tmp_path: Path) -> None:
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )
    vk_extractor = FakeMetadataExtractor(title="vk")
    fallback_extractor = FakeMetadataExtractor(title="fallback")
    router = RoutedMediaMetadataExtractor(
        vk_audio_extractor=vk_extractor,
        fallback_extractor=fallback_extractor,
    )

    metadata = router.extract(request)

    assert metadata.title == "fallback"
    assert vk_extractor.calls == 0
    assert fallback_extractor.calls == 1


def test_routed_preparer_uses_vk_audio_preparer_for_vk_audio_url(tmp_path: Path) -> None:
    task = build_vk_audio_task(target_dir=tmp_path)
    vk_preparer = FakeDownloadPreparer(title="vk")
    fallback_preparer = FakeDownloadPreparer(title="fallback")
    router = RoutedDownloadPreparer(
        vk_audio_preparer=vk_preparer,
        fallback_preparer=fallback_preparer,
    )

    router.prepare(task=task)

    assert vk_preparer.calls == 1
    assert fallback_preparer.calls == 0


def test_routed_downloader_uses_vk_audio_downloader_for_vk_audio_url(tmp_path: Path) -> None:
    task = build_vk_audio_task(target_dir=tmp_path)
    vk_downloader = FakeDownloader()
    fallback_downloader = FakeDownloader()
    router = RoutedDownloader(
        vk_audio_downloader=vk_downloader,
        fallback_downloader=fallback_downloader,
    )

    router.download(task=task)

    assert vk_downloader.calls == 1
    assert fallback_downloader.calls == 0
