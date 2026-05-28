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
