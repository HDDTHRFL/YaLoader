from __future__ import annotations

import pytest

from yaloader.infrastructure.github.app_update_checker import (
    GitHubAppUpdateCheckError,
    extract_latest_release_from_github_payload,
    extract_latest_release_version_from_github_payload,
    normalize_github_release_version,
)


def test_extract_latest_release_from_github_payload_uses_release_assets() -> None:
    release_info = extract_latest_release_from_github_payload(
        payload={
            "tag_name": "v1.2.3",
            "html_url": "https://github.com/HDDTHRFL/YaLoader/releases/tag/v1.2.3",
            "assets": [
                {
                    "name": "YaLoader.exe",
                    "browser_download_url": "https://example.test/YaLoader.exe",
                },
                {
                    "name": "YaLoader.exe.sha256",
                    "browser_download_url": "https://example.test/YaLoader.exe.sha256",
                },
            ],
        },
    )

    assert release_info.version == "1.2.3"
    assert release_info.executable_url == "https://example.test/YaLoader.exe"
    assert release_info.checksum_url == "https://example.test/YaLoader.exe.sha256"
    assert release_info.has_update_assets is True


def test_extract_latest_release_from_github_payload_allows_missing_assets() -> None:
    release_info = extract_latest_release_from_github_payload(
        payload={
            "tag_name": "v1.2.3",
            "assets": [],
        },
    )

    assert release_info.version == "1.2.3"
    assert release_info.executable_url is None
    assert release_info.checksum_url is None
    assert release_info.has_update_assets is False


def test_extract_latest_release_version_from_github_payload_keeps_compatibility() -> None:
    version = extract_latest_release_version_from_github_payload(
        payload={
            "tag_name": "v1.2.3",
            "assets": [],
        },
    )

    assert version == "1.2.3"


def test_normalize_github_release_version_accepts_plain_version() -> None:
    assert normalize_github_release_version(value="1.2.3") == "1.2.3"


def test_extract_latest_release_from_github_payload_rejects_invalid_payload() -> None:
    with pytest.raises(GitHubAppUpdateCheckError):
        extract_latest_release_from_github_payload(payload={"name": "1.2.3"})
