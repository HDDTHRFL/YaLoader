from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PreparedDownload(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    task_id: UUID
    url: str = Field(min_length=1)
    title: str | None = Field(default=None, min_length=1)
    playlist_count: int | None = Field(default=None, ge=1)
    duration_seconds: int | None = Field(default=None, ge=0)
    estimated_file_size_bytes: int | None = Field(default=None, ge=0)
    raw_info: dict[str, object] = Field(default_factory=dict)
