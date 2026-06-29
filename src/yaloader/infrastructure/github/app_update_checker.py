from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

import httpx

from yaloader.infrastructure.tools.version_detection import normalize_tool_version

GITHUB_LATEST_RELEASE_API_URL = "https://api.github.com/repos/HDDTHRFL/YaLoader/releases/latest"
GITHUB_API_TIMEOUT_SECONDS = 12.0


class GitHubAppUpdateCheckError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GitHubReleaseAppUpdateChecker:
    timeout_seconds: float = GITHUB_API_TIMEOUT_SECONDS

    def get_latest_version(self) -> str:
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=self.timeout_seconds,
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

        return extract_latest_release_version_from_github_payload(payload=payload)


def extract_latest_release_version_from_github_payload(*, payload: object) -> str:
    payload_mapping = ensure_mapping(value=payload, description="GitHub release response")
    tag_name = payload_mapping.get("tag_name")

    if not isinstance(tag_name, str):
        raise GitHubAppUpdateCheckError("ответ GitHub не содержит tag_name релиза")

    normalized_tag_name = tag_name.strip()

    if not normalized_tag_name:
        raise GitHubAppUpdateCheckError("ответ GitHub содержит пустой tag_name релиза")

    return normalize_github_release_version(value=normalized_tag_name)


def normalize_github_release_version(*, value: str) -> str:
    return normalize_tool_version(text=value.removeprefix("v").removeprefix("V"))


def ensure_mapping(*, value: object, description: str) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise GitHubAppUpdateCheckError(f"{description} имеет неожиданный формат")

    return cast(Mapping[object, object], value)
