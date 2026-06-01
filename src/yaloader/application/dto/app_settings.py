from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from yaloader.domain.download_speed_limit import validate_download_speed_limit_bytes_per_second


class AppSettings(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    downloads_dir: Path
    download_speed_limit_bytes_per_second: int | None = None

    @field_validator("downloads_dir")
    @classmethod
    def validate_downloads_dir(cls, value: Path) -> Path:
        if not value.is_absolute():
            message = "Downloads directory must be an absolute path."
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
