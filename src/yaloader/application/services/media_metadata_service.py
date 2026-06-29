from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.media_metadata import MediaMetadata
from yaloader.application.ports.media_metadata_extractor import MediaMetadataExtractor
from yaloader.domain.enums import DownloadMode, VideoQuality

VIDEO_QUALITY_HEIGHTS: Final[Mapping[VideoQuality, int]] = {
    VideoQuality.P2160: 2160,
    VideoQuality.P1440: 1440,
    VideoQuality.P1080: 1080,
    VideoQuality.P720: 720,
    VideoQuality.P480: 480,
    VideoQuality.P360: 360,
}

VIDEO_QUALITIES_DESC: Final[tuple[VideoQuality, ...]] = (
    VideoQuality.P2160,
    VideoQuality.P1440,
    VideoQuality.P1080,
    VideoQuality.P720,
    VideoQuality.P480,
    VideoQuality.P360,
)


@dataclass(frozen=True, slots=True)
class MediaMetadataService:
    extractor: MediaMetadataExtractor

    def resolve(self, *, request: DownloadRequest) -> MediaMetadata:
        probe = self.extractor.extract(request=request)
        resolved_video_quality = resolve_requested_video_quality(
            requested_quality=request.video_quality,
            available_heights=probe.available_video_heights,
            mode=request.mode,
        )

        return MediaMetadata(
            url=probe.url,
            title=probe.title,
            available_video_heights=probe.available_video_heights,
            requested_video_quality=request.video_quality,
            resolved_video_quality=resolved_video_quality,
            playlist_count=probe.playlist_count,
            duration_seconds=probe.duration_seconds,
            estimated_file_size_bytes=probe.estimated_file_size_bytes,
            is_file_size_estimated=probe.is_file_size_estimated,
        )


def resolve_requested_video_quality(
    *,
    requested_quality: VideoQuality,
    available_heights: tuple[int, ...],
    mode: DownloadMode,
) -> VideoQuality:
    if mode is DownloadMode.AUDIO:
        return requested_quality

    normalized_heights = tuple(sorted({height for height in available_heights if height > 0}))

    if not normalized_heights:
        return requested_quality

    if requested_quality is VideoQuality.BEST:
        return resolve_quality_from_height(height=max(normalized_heights))

    requested_height_limit = VIDEO_QUALITY_HEIGHTS[requested_quality]
    matching_heights = tuple(height for height in normalized_heights if height <= requested_height_limit)

    if not matching_heights:
        return requested_quality

    return resolve_quality_from_height(height=max(matching_heights))


def resolve_quality_from_height(*, height: int) -> VideoQuality:
    for quality in VIDEO_QUALITIES_DESC:
        quality_height = VIDEO_QUALITY_HEIGHTS[quality]

        if height >= quality_height:
            return quality

    return VideoQuality.P360
