from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from yaloader.domain.download_speed_limit import validate_download_speed_limit_bytes_per_second
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.domain.value_objects.media_url import MediaUrl


def get_current_utc_datetime() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class DownloadTask:
    task_id: UUID
    url: MediaUrl
    target_dir: Path
    mode: DownloadMode
    output_format: OutputFormat
    video_quality: VideoQuality
    requested_video_quality: VideoQuality
    include_playlist: bool
    playlist_count: int | None = None
    download_speed_limit_bytes_per_second: int | None = None
    status: DownloadStatus = DownloadStatus.PENDING
    created_at: datetime = field(default_factory=get_current_utc_datetime)
    title: str | None = None
    error_message: str | None = None

    @classmethod
    def create(
        cls,
        *,
        url: MediaUrl,
        target_dir: Path,
        mode: DownloadMode,
        output_format: OutputFormat,
        video_quality: VideoQuality,
        include_playlist: bool,
        download_speed_limit_bytes_per_second: int | None = None,
    ) -> DownloadTask:
        if not target_dir.is_absolute():
            message = "Download target directory must be an absolute path."
            raise ValueError(message)

        validated_download_speed_limit = validate_download_speed_limit_bytes_per_second(
            bytes_per_second=download_speed_limit_bytes_per_second,
        )

        return cls(
            task_id=uuid4(),
            url=url,
            target_dir=target_dir,
            mode=mode,
            output_format=output_format,
            video_quality=video_quality,
            requested_video_quality=video_quality,
            include_playlist=include_playlist,
            download_speed_limit_bytes_per_second=validated_download_speed_limit,
        )

    def with_status(
        self,
        *,
        status: DownloadStatus,
        error_message: str | None = None,
    ) -> DownloadTask:
        return replace(
            self,
            status=status,
            error_message=error_message,
        )

    def with_metadata(
        self,
        *,
        title: str | None,
        video_quality: VideoQuality,
        playlist_count: int | None = None,
    ) -> DownloadTask:
        return replace(
            self,
            title=title,
            video_quality=video_quality,
            playlist_count=playlist_count,
        )

    def with_download_speed_limit(
        self,
        *,
        download_speed_limit_bytes_per_second: int | None,
    ) -> DownloadTask:
        validated_download_speed_limit = validate_download_speed_limit_bytes_per_second(
            bytes_per_second=download_speed_limit_bytes_per_second,
        )

        return replace(
            self,
            download_speed_limit_bytes_per_second=validated_download_speed_limit,
        )
