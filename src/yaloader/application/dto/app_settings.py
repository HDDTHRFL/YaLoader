from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator


class AppSettings(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    downloads_dir: Path

    @field_validator("downloads_dir")
    @classmethod
    def validate_downloads_dir(cls, value: Path) -> Path:
        if not value.is_absolute():
            message = "Downloads directory must be an absolute path."
            raise ValueError(message)

        return value
