from __future__ import annotations

import pytest

from yaloader.infrastructure.github.app_update_checker import (
    GitHubAppUpdateCheckError,
    extract_latest_release_from_github_payload,
    extract_latest_release_version_from_github_payload,
    normalize_github_release_version,
    parse_github_asset_sha256_digest,
)

SHA256_TEXT = "a" * 64


def test_extract_latest_release_from_github_payload_uses_windows_zip_asset_digest() -> None:
    release_info = extract_latest_release_from_github_payload(
        payload={
            "tag_name": "v1.2.3",
            "html_url": "https://github.com/HDDTHRFL/YaLoader/releases/tag/v1.2.3",
            "assets": [
                {
                    "name": "YaLoader-v1.2.3-windows-x64.zip",
                    "browser_download_url": ("https://example.test/YaLoader-v1.2.3-windows-x64.zip"),
                    "digest": f"sha256:{SHA256_TEXT}",
                },
            ],
        },
    )

    assert release_info.version == "1.2.3"
    assert release_info.archive_name == "YaLoader-v1.2.3-windows-x64.zip"
    assert release_info.archive_url == "https://example.test/YaLoader-v1.2.3-windows-x64.zip"
    assert release_info.archive_sha256 == SHA256_TEXT
    assert release_info.has_update_assets is True


def test_extract_latest_release_from_github_payload_allows_missing_archive_asset() -> None:
    release_info = extract_latest_release_from_github_payload(
        payload={
            "tag_name": "v1.2.3",
            "assets": [],
        },
    )

    assert release_info.version == "1.2.3"
    assert release_info.archive_name is None
    assert release_info.archive_url is None
    assert release_info.archive_sha256 is None
    assert release_info.has_update_assets is False


def test_extract_latest_release_from_github_payload_requires_asset_digest() -> None:
    release_info = extract_latest_release_from_github_payload(
        payload={
            "tag_name": "v1.2.3",
            "assets": [
                {
                    "name": "YaLoader-v1.2.3-windows-x64.zip",
                    "browser_download_url": ("https://example.test/YaLoader-v1.2.3-windows-x64.zip"),
                },
            ],
        },
    )

    assert release_info.archive_url is not None
    assert release_info.archive_sha256 is None
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


def test_parse_github_asset_sha256_digest_accepts_sha256_prefix() -> None:
    assert parse_github_asset_sha256_digest(digest=f"sha256:{SHA256_TEXT}") == SHA256_TEXT


def test_parse_github_asset_sha256_digest_rejects_invalid_prefix() -> None:
    with pytest.raises(GitHubAppUpdateCheckError):
        parse_github_asset_sha256_digest(digest=f"md5:{SHA256_TEXT}")


def test_extract_latest_release_from_github_payload_rejects_invalid_payload() -> None:
    with pytest.raises(GitHubAppUpdateCheckError):
        extract_latest_release_from_github_payload(payload={"name": "1.2.3"})
