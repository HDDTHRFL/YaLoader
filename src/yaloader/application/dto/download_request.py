from __future__ import annotations

from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from yaloader.domain.download_speed_limit import validate_download_speed_limit_bytes_per_second
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality
from yaloader.domain.format_rules import AUDIO_OUTPUT_FORMATS, is_output_format_allowed
from yaloader.domain.source_policy import validate_supported_media_url
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
    separate_audio_video_enabled: bool = False
    separate_audio_format: OutputFormat = OutputFormat.MP3
    download_speed_limit_bytes_per_second: int | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        media_url = MediaUrl(value=value)
        return validate_supported_media_url(url=media_url.value)

    @field_validator("target_dir")
    @classmethod
    def validate_target_dir(cls, value: Path) -> Path:
        if not value.is_absolute():
            msg = "Target directory must be an absolute path."
            raise ValueError(msg)

        return value

    @field_validator("separate_audio_format")
    @classmethod
    def validate_separate_audio_format(cls, value: OutputFormat) -> OutputFormat:
        if value not in AUDIO_OUTPUT_FORMATS:
            message = "Separate audio format must be an audio output format."
            raise ValueError(message)

        return value

    @field_validator("download_speed_limit_bytes_per_second", mode="before")
    @classmethod
    def validate_download_speed_limit(cls, value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, bool):
            message = "Download speed limit must be an integer number of bytes per second."
            raise ValueError(message)

        if isinstance(value, int):
            return validate_download_speed_limit_bytes_per_second(bytes_per_second=value)

        return value

    @model_validator(mode="after")
    def validate_output_format_matches_mode(self) -> Self:
        if not is_output_format_allowed(mode=self.mode, output_format=self.output_format):
            message = (
                f"Output format '{self.output_format.value}' is not allowed "
                f"for download mode '{self.mode.value}'."
            )
            raise ValueError(message)

        return self
