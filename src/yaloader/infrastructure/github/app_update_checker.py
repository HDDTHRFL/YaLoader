from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

import httpx

from yaloader.application.dto.app_update import (
    GITHUB_RELEASES_URL,
    AppReleaseInfo,
    build_yaloader_windows_x64_archive_name,
)
from yaloader.infrastructure.tools.checksum import ChecksumError, validate_sha256_hex
from yaloader.infrastructure.tools.version_detection import normalize_tool_version

GITHUB_LATEST_RELEASE_API_URL: Final = "https://api.github.com/repos/HDDTHRFL/YaLoader/releases/latest"
GITHUB_API_TIMEOUT_SECONDS: Final = 12.0
GITHUB_API_USER_AGENT: Final = "YaLoader"
GITHUB_SHA256_DIGEST_PREFIX: Final = "sha256:"


class GitHubAppUpdateCheckError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GitHubReleaseAsset:
    name: str
    download_url: str
    sha256: str | None = None


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
            raise GitHubAppUpdateCheckError(f"GitHub вернул HTTP {error.response.status_code}") from error
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
    version = normalize_github_release_version(value=tag_name)
    releases_url = extract_optional_text(mapping=payload_mapping, key="html_url") or GITHUB_RELEASES_URL
    archive_asset = find_yaloader_windows_x64_archive_asset(
        payload=payload_mapping,
        version=version,
    )

    return AppReleaseInfo(
        version=version,
        releases_url=releases_url,
        archive_name=None if archive_asset is None else archive_asset.name,
        archive_url=None if archive_asset is None else archive_asset.download_url,
        archive_sha256=None if archive_asset is None else archive_asset.sha256,
    )


def find_yaloader_windows_x64_archive_asset(
    *,
    payload: Mapping[object, object],
    version: str,
) -> GitHubReleaseAsset | None:
    expected_asset_name = build_yaloader_windows_x64_archive_name(version=version)

    for asset in extract_release_assets(payload=payload):
        if asset.name.casefold() == expected_asset_name.casefold():
            return asset

    return None


def extract_release_assets(*, payload: Mapping[object, object]) -> tuple[GitHubReleaseAsset, ...]:
    assets = payload.get("assets")

    if assets is None:
        return ()

    if isinstance(assets, (str, bytes)) or not isinstance(assets, Sequence):
        raise GitHubAppUpdateCheckError("поле assets в ответе GitHub имеет неожиданный формат")

    release_assets: list[GitHubReleaseAsset] = []

    for asset in assets:
        asset_mapping = ensure_mapping(value=asset, description="GitHub release asset")
        asset_name = extract_required_text(
            mapping=asset_mapping,
            key="name",
            description="name release asset",
        )
        download_url = extract_required_text(
            mapping=asset_mapping,
            key="browser_download_url",
            description=f"browser_download_url для {asset_name}",
        )
        release_assets.append(
            GitHubReleaseAsset(
                name=asset_name,
                download_url=download_url,
                sha256=extract_github_asset_sha256(mapping=asset_mapping),
            )
        )

    return tuple(release_assets)


def extract_github_asset_sha256(*, mapping: Mapping[object, object]) -> str | None:
    digest = extract_optional_text(mapping=mapping, key="digest")

    if digest is None:
        return None

    return parse_github_asset_sha256_digest(digest=digest)


def parse_github_asset_sha256_digest(*, digest: str) -> str:
    normalized_digest = digest.strip().casefold()

    if not normalized_digest.startswith(GITHUB_SHA256_DIGEST_PREFIX):
        raise GitHubAppUpdateCheckError(f"GitHub asset digest должен начинаться с {GITHUB_SHA256_DIGEST_PREFIX}")

    sha256 = normalized_digest.removeprefix(GITHUB_SHA256_DIGEST_PREFIX).strip()

    try:
        validate_sha256_hex(value=sha256)
    except ChecksumError as error:
        raise GitHubAppUpdateCheckError(f"GitHub asset digest содержит неверный SHA-256: {error}") from error

    return sha256


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
