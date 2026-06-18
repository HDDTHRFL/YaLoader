from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from yaloader.domain.download_speed_limit import validate_download_speed_limit_bytes_per_second
from yaloader.domain.enums import OutputFormat
from yaloader.domain.format_rules import AUDIO_OUTPUT_FORMATS


class AppSettings(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    downloads_dir: Path
    download_speed_limit_bytes_per_second: int | None = None
    show_history_on_startup: bool = False
    open_downloads_dir_after_queue_completed: bool = False
    confirm_clear_queue: bool = True
    separate_audio_video_enabled: bool = False
    separate_audio_video_audio_format: OutputFormat = OutputFormat.MP3

    @field_validator("downloads_dir")
    @classmethod
    def validate_downloads_dir(cls, value: Path) -> Path:
        if not value.is_absolute():
            message = "Downloads directory must be an absolute path."
            raise ValueError(message)

        return value

    @field_validator("separate_audio_video_audio_format")
    @classmethod
    def validate_separate_audio_video_audio_format(
        cls,
        value: OutputFormat,
    ) -> OutputFormat:
        if value not in AUDIO_OUTPUT_FORMATS:
            message = "Separate audio/video audio format must be an audio output format."
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
