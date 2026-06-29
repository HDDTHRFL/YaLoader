from __future__ import annotations

import importlib.metadata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

import httpx

from yaloader.application.dto.tool_installation import ToolId
from yaloader.application.ports.ytdlp_runtime import YtDlpRuntimeInfoProvider

YTDLP_PACKAGE_NAME: Final = "yt-dlp"
YTDLP_PYPI_JSON_URL: Final = "https://pypi.org/pypi/yt-dlp/json"
YTDLP_VERSION_CHECK_TIMEOUT_SECONDS: Final = 8.0


class YtDlpVersionCheckError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class YtDlpPackageVersionChecker:
    timeout_seconds: float = YTDLP_VERSION_CHECK_TIMEOUT_SECONDS
    runtime_provider: YtDlpRuntimeInfoProvider | None = None

    @property
    def tool_id(self) -> ToolId:
        return ToolId.YTDLP

    def get_current_version(self) -> str:
        if self.runtime_provider is not None:
            return self.runtime_provider.get_runtime_info().version

        try:
            return importlib.metadata.version(YTDLP_PACKAGE_NAME)
        except importlib.metadata.PackageNotFoundError as error:
            raise YtDlpVersionCheckError("пакет yt-dlp не найден") from error

    def get_latest_version(self) -> str:
        with httpx.Client(
            follow_redirects=True,
            timeout=self.timeout_seconds,
        ) as client:
            response = client.get(YTDLP_PYPI_JSON_URL)
            response.raise_for_status()
            payload = cast(object, response.json())

        return extract_latest_version_from_pypi_payload(payload=payload)


def extract_latest_version_from_pypi_payload(*, payload: object) -> str:
    payload_mapping = ensure_mapping(value=payload, description="PyPI response")
    info = payload_mapping.get("info")
    info_mapping = ensure_mapping(value=info, description="PyPI info")
    version = info_mapping.get("version")

    if not isinstance(version, str):
        raise YtDlpVersionCheckError("ответ PyPI не содержит версию yt-dlp")

    normalized_version = version.strip()

    if not normalized_version:
        raise YtDlpVersionCheckError("ответ PyPI содержит пустую версию yt-dlp")

    return normalized_version


def ensure_mapping(*, value: object, description: str) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise YtDlpVersionCheckError(f"{description} имеет неожиданный формат")

    return cast(Mapping[object, object], value)
