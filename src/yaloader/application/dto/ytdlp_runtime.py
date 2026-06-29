from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class YtDlpRuntimeSource(StrEnum):
    BUNDLED = "bundled"
    EXTERNAL = "external"


class YtDlpRuntimeInfo(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    source: YtDlpRuntimeSource
    version: str = Field(min_length=1)
    path: Path | None = None
    fallback_reason: str | None = Field(default=None, min_length=1)

    @property
    def is_external(self) -> bool:
        return self.source is YtDlpRuntimeSource.EXTERNAL

    @property
    def is_bundled(self) -> bool:
        return self.source is YtDlpRuntimeSource.BUNDLED

    @classmethod
    def bundled(
        cls,
        *,
        version: str,
        fallback_reason: str | None = None,
    ) -> YtDlpRuntimeInfo:
        return cls(
            source=YtDlpRuntimeSource.BUNDLED,
            version=version,
            fallback_reason=fallback_reason,
        )

    @classmethod
    def external(
        cls,
        *,
        version: str,
        path: Path,
    ) -> YtDlpRuntimeInfo:
        return cls(
            source=YtDlpRuntimeSource.EXTERNAL,
            version=version,
            path=path,
        )
