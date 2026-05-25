from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality
from yaloader.domain.value_objects.media_url import MediaUrl


class DownloadRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    url: str = Field(min_length=1)
    target_dir: Path
    mode: DownloadMode = DownloadMode.VIDEO
    output_format: OutputFormat = OutputFormat.MP4
    video_quality: VideoQuality = VideoQuality.BEST
    include_playlist: bool = False

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return MediaUrl(value=value).value

    @field_validator("target_dir")
    @classmethod
    def validate_target_dir(cls, value: Path) -> Path:
        if not value.is_absolute():
            msg = "Target directory must be an absolute path."
            raise ValueError(msg)

        return value
