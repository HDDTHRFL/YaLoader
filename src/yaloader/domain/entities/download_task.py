from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

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
    include_playlist: bool
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
    ) -> DownloadTask:
        if not target_dir.is_absolute():
            message = "Download target directory must be an absolute path."
            raise ValueError(message)

        return cls(
            task_id=uuid4(),
            url=url,
            target_dir=target_dir,
            mode=mode,
            output_format=output_format,
            video_quality=video_quality,
            include_playlist=include_playlist,
        )
