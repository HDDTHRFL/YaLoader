from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

import httpx

from yaloader.application.dto.app_update import (
    GITHUB_RELEASES_URL,
    YALOADER_EXE_ASSET_NAME,
    YALOADER_EXE_SHA256_ASSET_NAME,
    AppReleaseInfo,
)
from yaloader.infrastructure.tools.version_detection import normalize_tool_version

GITHUB_LATEST_RELEASE_API_URL: Final = (
    "https://api.github.com/repos/HDDTHRFL/YaLoader/releases/latest"
)
GITHUB_API_TIMEOUT_SECONDS: Final = 12.0
GITHUB_API_USER_AGENT: Final = "YaLoader"


class GitHubAppUpdateCheckError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GitHubReleaseAppUpdateChecker:
    timeout_seconds: float = GITHUB_API_TIMEOUT_SECONDS

    def get_latest_release(self) -> AppReleaseInfo:
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=self.timeout_seconds,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": GITHUB_API_USER_AGENT,
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            ) as client:
                response = client.get(GITHUB_LATEST_RELEASE_API_URL)
                response.raise_for_status()
                payload = cast(object, response.json())
        except httpx.HTTPStatusError as error:
            raise GitHubAppUpdateCheckError(
                f"GitHub вернул HTTP {error.response.status_code}"
            ) from error
        except httpx.HTTPError as error:
            raise GitHubAppUpdateCheckError(f"GitHub недоступен: {error}") from error

        return extract_latest_release_from_github_payload(payload=payload)


def extract_latest_release_from_github_payload(*, payload: object) -> AppReleaseInfo:
    payload_mapping = ensure_mapping(value=payload, description="GitHub release response")
    tag_name = extract_required_text(
        mapping=payload_mapping,
        key="tag_name",
        description="tag_name релиза",
    )
    releases_url = (
        extract_optional_text(mapping=payload_mapping, key="html_url") or GITHUB_RELEASES_URL
    )

    return AppReleaseInfo(
        version=normalize_github_release_version(value=tag_name),
        releases_url=releases_url,
        executable_url=find_release_asset_download_url(
            payload=payload_mapping,
            asset_name=YALOADER_EXE_ASSET_NAME,
        ),
        checksum_url=find_release_asset_download_url(
            payload=payload_mapping,
            asset_name=YALOADER_EXE_SHA256_ASSET_NAME,
        ),
    )


def find_release_asset_download_url(
    *,
    payload: Mapping[object, object],
    asset_name: str,
) -> str | None:
    assets = payload.get("assets")

    if assets is None:
        return None

    if isinstance(assets, (str, bytes)) or not isinstance(assets, Sequence):
        raise GitHubAppUpdateCheckError("поле assets в ответе GitHub имеет неожиданный формат")

    for asset in assets:
        asset_mapping = ensure_mapping(value=asset, description="GitHub release asset")
        current_asset_name = extract_optional_text(mapping=asset_mapping, key="name")

        if current_asset_name != asset_name:
            continue

        return extract_required_text(
            mapping=asset_mapping,
            key="browser_download_url",
            description=f"browser_download_url для {asset_name}",
        )

    return None


def normalize_github_release_version(*, value: str) -> str:
    return normalize_tool_version(text=value.removeprefix("v").removeprefix("V"))


def extract_required_text(
    *,
    mapping: Mapping[object, object],
    key: str,
    description: str,
) -> str:
    value = extract_optional_text(mapping=mapping, key=key)

    if value is None:
        raise GitHubAppUpdateCheckError(f"ответ GitHub не содержит {description}")

    return value


def extract_optional_text(*, mapping: Mapping[object, object], key: str) -> str | None:
    value = mapping.get(key)

    if not isinstance(value, str):
        return None

    normalized_value = value.strip()

    if not normalized_value:
        return None

    return normalized_value


def ensure_mapping(*, value: object, description: str) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise GitHubAppUpdateCheckError(f"{description} имеет неожиданный формат")

    return cast(Mapping[object, object], value)


def extract_latest_release_version_from_github_payload(*, payload: object) -> str:
    return extract_latest_release_from_github_payload(payload=payload).version
