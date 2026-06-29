from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

GITHUB_RELEASES_URL: Final = "https://github.com/HDDTHRFL/YaLoader/releases"


class AppUpdateCheckStatus(StrEnum):
    UPDATE_AVAILABLE = "update_available"
    UP_TO_DATE = "up_to_date"
    CHECK_FAILED = "check_failed"


class AppUpdateCheckResult(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    status: AppUpdateCheckStatus
    current_version: str = Field(min_length=1)
    message: str = Field(min_length=1)
    latest_version: str | None = Field(default=None, min_length=1)
    releases_url: str = Field(default=GITHUB_RELEASES_URL, min_length=1)

    @property
    def should_update(self) -> bool:
        return self.status is AppUpdateCheckStatus.UPDATE_AVAILABLE

    @property
    def is_success(self) -> bool:
        return self.status in {
            AppUpdateCheckStatus.UPDATE_AVAILABLE,
            AppUpdateCheckStatus.UP_TO_DATE,
        }

    @classmethod
    def update_available(
        cls,
        *,
        current_version: str,
        latest_version: str,
        releases_url: str = GITHUB_RELEASES_URL,
    ) -> AppUpdateCheckResult:
        return cls(
            status=AppUpdateCheckStatus.UPDATE_AVAILABLE,
            current_version=current_version,
            latest_version=latest_version,
            releases_url=releases_url,
            message=f"Доступна новая версия YaLoader {latest_version}",
        )

    @classmethod
    def up_to_date(
        cls,
        *,
        current_version: str,
        latest_version: str,
        releases_url: str = GITHUB_RELEASES_URL,
    ) -> AppUpdateCheckResult:
        return cls(
            status=AppUpdateCheckStatus.UP_TO_DATE,
            current_version=current_version,
            latest_version=latest_version,
            releases_url=releases_url,
            message=f"YaLoader актуален: {current_version}",
        )

    @classmethod
    def check_failed(
        cls,
        *,
        current_version: str,
        message: str,
        releases_url: str = GITHUB_RELEASES_URL,
    ) -> AppUpdateCheckResult:
        return cls(
            status=AppUpdateCheckStatus.CHECK_FAILED,
            current_version=current_version,
            releases_url=releases_url,
            message=message,
        )
