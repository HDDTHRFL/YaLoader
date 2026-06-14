from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from yaloader.domain.enums import VideoQuality


class MediaMetadataProbe(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    url: str = Field(min_length=1)
    title: str | None = None
    available_video_heights: tuple[int, ...] = ()
    playlist_count: int | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    estimated_file_size_bytes: int | None = Field(default=None, ge=0)
    is_file_size_estimated: bool = False


class MediaMetadata(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    url: str = Field(min_length=1)
    title: str | None = None
    available_video_heights: tuple[int, ...] = ()
    requested_video_quality: VideoQuality
    resolved_video_quality: VideoQuality
    playlist_count: int | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    estimated_file_size_bytes: int | None = Field(default=None, ge=0)
    is_file_size_estimated: bool = False
