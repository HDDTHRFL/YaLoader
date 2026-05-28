from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.media_metadata import MediaMetadataProbe
from yaloader.application.services.media_metadata_service import MediaMetadataService
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality


@dataclass(frozen=True, slots=True)
class FakeMediaMetadataExtractor:
    probe: MediaMetadataProbe

    def extract(self, request: DownloadRequest) -> MediaMetadataProbe:
        return self.probe


def test_best_quality_resolves_to_highest_available_quality(tmp_path: Path) -> None:
    request = create_video_request(
        target_dir=tmp_path,
        video_quality=VideoQuality.BEST,
    )
    service = MediaMetadataService(
        extractor=FakeMediaMetadataExtractor(
            probe=MediaMetadataProbe(
                url=request.url,
                title="Test video",
                available_video_heights=(1080, 720, 480),
            )
        )
    )

    metadata = service.resolve(request=request)

    assert metadata.title == "Test video"
    assert metadata.requested_video_quality is VideoQuality.BEST
    assert metadata.resolved_video_quality is VideoQuality.P1080


def test_unavailable_requested_quality_falls_back_to_best_lower_available_quality(
    tmp_path: Path,
) -> None:
    request = create_video_request(
        target_dir=tmp_path,
        video_quality=VideoQuality.P2160,
    )
    service = MediaMetadataService(
        extractor=FakeMediaMetadataExtractor(
            probe=MediaMetadataProbe(
                url=request.url,
                available_video_heights=(720, 480),
            )
        )
    )

    metadata = service.resolve(request=request)

    assert metadata.resolved_video_quality is VideoQuality.P720


def test_requested_quality_falls_back_to_480p_when_720p_is_missing(
    tmp_path: Path,
) -> None:
    request = create_video_request(
        target_dir=tmp_path,
        video_quality=VideoQuality.P720,
    )
    service = MediaMetadataService(
        extractor=FakeMediaMetadataExtractor(
            probe=MediaMetadataProbe(
                url=request.url,
                available_video_heights=(1080, 480, 360),
            )
        )
    )

    metadata = service.resolve(request=request)

    assert metadata.resolved_video_quality is VideoQuality.P480


def test_metadata_service_keeps_requested_quality_when_no_heights_are_available(
    tmp_path: Path,
) -> None:
    request = create_video_request(
        target_dir=tmp_path,
        video_quality=VideoQuality.P1080,
    )
    service = MediaMetadataService(
        extractor=FakeMediaMetadataExtractor(
            probe=MediaMetadataProbe(
                url=request.url,
                available_video_heights=(),
            )
        )
    )

    metadata = service.resolve(request=request)

    assert metadata.resolved_video_quality is VideoQuality.P1080


def test_audio_request_keeps_requested_quality(tmp_path: Path) -> None:
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        mode=DownloadMode.AUDIO,
        output_format=OutputFormat.MP3,
        video_quality=VideoQuality.BEST,
    )
    service = MediaMetadataService(
        extractor=FakeMediaMetadataExtractor(
            probe=MediaMetadataProbe(
                url=request.url,
                available_video_heights=(1080, 720),
            )
        )
    )

    metadata = service.resolve(request=request)

    assert metadata.resolved_video_quality is VideoQuality.BEST


def create_video_request(
    *,
    target_dir: Path,
    video_quality: VideoQuality,
) -> DownloadRequest:
    return DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=target_dir,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=video_quality,
    )
