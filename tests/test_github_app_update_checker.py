from __future__ import annotations

import pytest

from yaloader.infrastructure.github.app_update_checker import (
    GitHubAppUpdateCheckError,
    extract_latest_release_version_from_github_payload,
    normalize_github_release_version,
)


def test_extract_latest_release_version_from_github_payload_uses_tag_name() -> None:
    version = extract_latest_release_version_from_github_payload(
        payload={
            "tag_name": "v1.2.3",
        },
    )

    assert version == "1.2.3"


def test_normalize_github_release_version_accepts_plain_version() -> None:
    assert normalize_github_release_version(value="1.2.3") == "1.2.3"


def test_extract_latest_release_version_from_github_payload_rejects_invalid_payload() -> None:
    with pytest.raises(GitHubAppUpdateCheckError):
        extract_latest_release_version_from_github_payload(payload={"name": "1.2.3"})
