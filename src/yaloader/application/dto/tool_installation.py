from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ToolId(StrEnum):
    FFMPEG = "ffmpeg"
    DENO = "deno"
    YTDLP = "yt-dlp"


class ToolInstallationStatus(StrEnum):
    AVAILABLE = "available"
    INSTALLED = "installed"
    MISSING = "missing"
    NOT_CONFIGURED = "not_configured"
    FAILED = "failed"


class ToolUpdateCheckStatus(StrEnum):
    UPDATE_AVAILABLE = "update_available"
    UP_TO_DATE = "up_to_date"
    MISSING = "missing"
    CHECK_FAILED = "check_failed"


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


class ToolUpdateCheckResult(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    tool_id: ToolId
    status: ToolUpdateCheckStatus
    message: str = Field(min_length=1)
    current_version: str | None = None
    latest_version: str | None = None
    executable_path: Path | None = None

    @property
    def should_update(self) -> bool:
        return self.status is ToolUpdateCheckStatus.UPDATE_AVAILABLE

    @property
    def is_success(self) -> bool:
        return self.status in {
            ToolUpdateCheckStatus.UPDATE_AVAILABLE,
            ToolUpdateCheckStatus.UP_TO_DATE,
        }

    @classmethod
    def update_available(
        cls,
        *,
        tool_id: ToolId,
        current_version: str,
        latest_version: str,
        executable_path: Path | None = None,
    ) -> ToolUpdateCheckResult:
        return cls(
            tool_id=tool_id,
            status=ToolUpdateCheckStatus.UPDATE_AVAILABLE,
            current_version=current_version,
            latest_version=latest_version,
            executable_path=executable_path,
            message=f"{tool_id.value}: доступна версия {latest_version}",
        )

    @classmethod
    def up_to_date(
        cls,
        *,
        tool_id: ToolId,
        current_version: str,
        latest_version: str,
        executable_path: Path | None = None,
    ) -> ToolUpdateCheckResult:
        return cls(
            tool_id=tool_id,
            status=ToolUpdateCheckStatus.UP_TO_DATE,
            current_version=current_version,
            latest_version=latest_version,
            executable_path=executable_path,
            message=f"{tool_id.value}: актуальная версия {current_version}",
        )

    @classmethod
    def missing(cls, *, tool_id: ToolId) -> ToolUpdateCheckResult:
        return cls(
            tool_id=tool_id,
            status=ToolUpdateCheckStatus.MISSING,
            message=f"{tool_id.value}: не найден",
        )

    @classmethod
    def check_failed(
        cls,
        *,
        tool_id: ToolId,
        message: str,
        executable_path: Path | None = None,
    ) -> ToolUpdateCheckResult:
        return cls(
            tool_id=tool_id,
            status=ToolUpdateCheckStatus.CHECK_FAILED,
            message=message,
            executable_path=executable_path,
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
