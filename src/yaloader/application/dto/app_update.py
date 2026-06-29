from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

GITHUB_RELEASES_URL: Final = "https://github.com/HDDTHRFL/YaLoader/releases"
YALOADER_EXE_ASSET_NAME: Final = "YaLoader.exe"
YALOADER_EXE_SHA256_ASSET_NAME: Final = "YaLoader.exe.sha256"


class AppUpdateCheckStatus(StrEnum):
    UPDATE_AVAILABLE = "update_available"
    UP_TO_DATE = "up_to_date"
    CHECK_FAILED = "check_failed"


class AppUpdateInstallStatus(StrEnum):
    READY_TO_RESTART = "ready_to_restart"
    FAILED = "failed"


class AppReleaseInfo(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    version: str = Field(min_length=1)
    releases_url: str = Field(default=GITHUB_RELEASES_URL, min_length=1)
    executable_url: str | None = Field(default=None, min_length=1)
    checksum_url: str | None = Field(default=None, min_length=1)

    @property
    def has_update_assets(self) -> bool:
        return self.executable_url is not None and self.checksum_url is not None


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
    release_info: AppReleaseInfo | None = None

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
        release_info: AppReleaseInfo,
    ) -> AppUpdateCheckResult:
        return cls(
            status=AppUpdateCheckStatus.UPDATE_AVAILABLE,
            current_version=current_version,
            latest_version=release_info.version,
            releases_url=release_info.releases_url,
            release_info=release_info,
            message=f"Доступна новая версия YaLoader {release_info.version}",
        )

    @classmethod
    def up_to_date(
        cls,
        *,
        current_version: str,
        release_info: AppReleaseInfo,
    ) -> AppUpdateCheckResult:
        return cls(
            status=AppUpdateCheckStatus.UP_TO_DATE,
            current_version=current_version,
            latest_version=release_info.version,
            releases_url=release_info.releases_url,
            release_info=release_info,
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


class AppUpdateInstallResult(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    status: AppUpdateInstallStatus
    message: str = Field(min_length=1)
    installed_version: str | None = Field(default=None, min_length=1)

    @property
    def should_restart(self) -> bool:
        return self.status is AppUpdateInstallStatus.READY_TO_RESTART

    @property
    def is_success(self) -> bool:
        return self.status is AppUpdateInstallStatus.READY_TO_RESTART

    @classmethod
    def ready_to_restart(
        cls,
        *,
        installed_version: str,
    ) -> AppUpdateInstallResult:
        return cls(
            status=AppUpdateInstallStatus.READY_TO_RESTART,
            installed_version=installed_version,
            message=(
                f"Обновление YaLoader {installed_version} подготовлено. "
                "Приложение будет закрыто и запущено заново."
            ),
        )

    @classmethod
    def failed(cls, *, message: str) -> AppUpdateInstallResult:
        return cls(
            status=AppUpdateInstallStatus.FAILED,
            message=message,
        )
