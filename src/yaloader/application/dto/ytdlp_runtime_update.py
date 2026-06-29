from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from yaloader.application.dto.ytdlp_runtime import YtDlpRuntimeInfo


class YtDlpRuntimeUpdateStatus(StrEnum):
    INSTALLED = "installed"
    RESET = "reset"
    NOT_INSTALLED = "not_installed"
    FAILED = "failed"


class YtDlpRuntimeUpdateProgress(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    message: str = Field(min_length=1)
    percent: int | None = Field(default=None, ge=0, le=100)
    path: Path | None = None


class YtDlpRuntimeUpdateResult(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    status: YtDlpRuntimeUpdateStatus
    message: str = Field(min_length=1)
    runtime_info: YtDlpRuntimeInfo | None = None

    @property
    def is_success(self) -> bool:
        return self.status in {
            YtDlpRuntimeUpdateStatus.INSTALLED,
            YtDlpRuntimeUpdateStatus.RESET,
            YtDlpRuntimeUpdateStatus.NOT_INSTALLED,
        }

    @classmethod
    def installed(cls, *, runtime_info: YtDlpRuntimeInfo) -> YtDlpRuntimeUpdateResult:
        return cls(
            status=YtDlpRuntimeUpdateStatus.INSTALLED,
            message=f"yt-dlp {runtime_info.version} установлен как пользовательский runtime",
            runtime_info=runtime_info,
        )

    @classmethod
    def reset(cls, *, runtime_info: YtDlpRuntimeInfo) -> YtDlpRuntimeUpdateResult:
        return cls(
            status=YtDlpRuntimeUpdateStatus.RESET,
            message=f"yt-dlp сброшен до встроенной версии {runtime_info.version}",
            runtime_info=runtime_info,
        )

    @classmethod
    def not_installed(cls, *, runtime_info: YtDlpRuntimeInfo) -> YtDlpRuntimeUpdateResult:
        return cls(
            status=YtDlpRuntimeUpdateStatus.NOT_INSTALLED,
            message=(
                "Пользовательский yt-dlp не установлен. "
                f"Активна встроенная версия {runtime_info.version}"
            ),
            runtime_info=runtime_info,
        )

    @classmethod
    def failed(cls, *, message: str) -> YtDlpRuntimeUpdateResult:
        return cls(
            status=YtDlpRuntimeUpdateStatus.FAILED,
            message=message,
        )


def build_ytdlp_runtime_update_progress(
    *,
    message: str,
    percent: int | None = None,
    path: Path | None = None,
) -> YtDlpRuntimeUpdateProgress:
    return YtDlpRuntimeUpdateProgress(
        message=message,
        percent=percent,
        path=path,
    )
