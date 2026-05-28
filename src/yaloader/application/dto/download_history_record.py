from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from yaloader.domain.entities.download_task import DownloadTask, get_current_utc_datetime
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality


class DownloadHistoryRecord(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    task_id: UUID
    url: str = Field(min_length=1)
    target_dir: Path
    mode: DownloadMode
    output_format: OutputFormat
    video_quality: VideoQuality
    status: DownloadStatus
    created_at: datetime
    finished_at: datetime
    output_path: Path | None = None
    error_message: str | None = None

    @classmethod
    def create_from_task(
        cls,
        *,
        task: DownloadTask,
        output_path: Path | None = None,
    ) -> DownloadHistoryRecord:
        return cls(
            task_id=task.task_id,
            url=task.url.value,
            target_dir=task.target_dir,
            mode=task.mode,
            output_format=task.output_format,
            video_quality=task.video_quality,
            status=task.status,
            created_at=task.created_at,
            finished_at=get_current_utc_datetime(),
            output_path=output_path,
            error_message=task.error_message,
        )
