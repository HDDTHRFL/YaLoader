from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class BrowserId(StrEnum):
    FIREFOX = "firefox"


class BrowserCookiesExportStatus(StrEnum):
    EXPORTED = "exported"
    FAILED = "failed"


class BrowserCookiesExportProgress(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    browser_id: BrowserId
    message: str = Field(min_length=1)
    percent: int | None = Field(default=None, ge=0, le=100)
    path: Path | None = None


class BrowserCookiesExportResult(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    browser_id: BrowserId
    status: BrowserCookiesExportStatus
    message: str = Field(min_length=1)
    cookies_file: Path | None = None

    @property
    def is_success(self) -> bool:
        return self.status is BrowserCookiesExportStatus.EXPORTED

    @classmethod
    def exported(
        cls,
        *,
        browser_id: BrowserId,
        cookies_file: Path,
    ) -> BrowserCookiesExportResult:
        return cls(
            browser_id=browser_id,
            status=BrowserCookiesExportStatus.EXPORTED,
            message=f"cookies.txt создан из {browser_id.value}",
            cookies_file=cookies_file,
        )

    @classmethod
    def failed(
        cls,
        *,
        browser_id: BrowserId,
        message: str,
    ) -> BrowserCookiesExportResult:
        return cls(
            browser_id=browser_id,
            status=BrowserCookiesExportStatus.FAILED,
            message=message,
        )


def build_browser_cookies_export_progress(
    *,
    browser_id: BrowserId,
    message: str,
    percent: int | None = None,
    path: Path | None = None,
) -> BrowserCookiesExportProgress:
    return BrowserCookiesExportProgress(
        browser_id=browser_id,
        message=message,
        percent=percent,
        path=path,
    )
