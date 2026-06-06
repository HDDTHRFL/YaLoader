from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ToolId(StrEnum):
    FFMPEG = "ffmpeg"
    DENO = "deno"


class ToolInstallationStatus(StrEnum):
    AVAILABLE = "available"
    INSTALLED = "installed"
    MISSING = "missing"
    NOT_CONFIGURED = "not_configured"
    FAILED = "failed"


class ToolInstallationProgress(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    tool_id: ToolId
    message: str = Field(min_length=1)
    percent: int | None = Field(default=None, ge=0, le=100)
    path: Path | None = None


class ToolInstallationResult(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    tool_id: ToolId
    status: ToolInstallationStatus
    message: str = Field(min_length=1)
    executable_path: Path | None = None

    @property
    def is_success(self) -> bool:
        return self.status in {
            ToolInstallationStatus.AVAILABLE,
            ToolInstallationStatus.INSTALLED,
        }

    @classmethod
    def available(
        cls,
        *,
        tool_id: ToolId,
        executable_path: Path,
    ) -> ToolInstallationResult:
        return cls(
            tool_id=tool_id,
            status=ToolInstallationStatus.AVAILABLE,
            message=f"{tool_id.value} уже доступен",
            executable_path=executable_path,
        )

    @classmethod
    def installed(
        cls,
        *,
        tool_id: ToolId,
        executable_path: Path,
    ) -> ToolInstallationResult:
        return cls(
            tool_id=tool_id,
            status=ToolInstallationStatus.INSTALLED,
            message=f"{tool_id.value} установлен",
            executable_path=executable_path,
        )

    @classmethod
    def missing(cls, *, tool_id: ToolId) -> ToolInstallationResult:
        return cls(
            tool_id=tool_id,
            status=ToolInstallationStatus.MISSING,
            message=f"{tool_id.value} не найден",
        )

    @classmethod
    def not_configured(cls, *, tool_id: ToolId) -> ToolInstallationResult:
        return cls(
            tool_id=tool_id,
            status=ToolInstallationStatus.NOT_CONFIGURED,
            message=f"Установщик {tool_id.value} пока не настроен",
        )

    @classmethod
    def failed(cls, *, tool_id: ToolId, message: str) -> ToolInstallationResult:
        return cls(
            tool_id=tool_id,
            status=ToolInstallationStatus.FAILED,
            message=message,
        )


def build_tool_installation_progress(
    *,
    tool_id: ToolId,
    message: str,
    percent: int | None = None,
    path: Path | None = None,
) -> ToolInstallationProgress:
    return ToolInstallationProgress(
        tool_id=tool_id,
        message=message,
        percent=percent,
        path=path,
    )
