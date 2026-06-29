from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class EnvironmentItemStatus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    is_ok: bool
    message: str
    path: Path | None = None


class EnvironmentStatus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ffmpeg: EnvironmentItemStatus
    deno: EnvironmentItemStatus
    ytdlp: EnvironmentItemStatus
    cookies: EnvironmentItemStatus
    downloads_dir: EnvironmentItemStatus

    @property
    def is_ready_for_basic_downloads(self) -> bool:
        return self.ffmpeg.is_ok and self.deno.is_ok and self.ytdlp.is_ok and self.downloads_dir.is_ok
