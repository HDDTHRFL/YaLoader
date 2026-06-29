from __future__ import annotations

import pytest

from yaloader.infrastructure.ytdlp.runtime_installer import (
    YtDlpRuntimeInstallationError,
    are_ytdlp_versions_equivalent,
    extract_latest_ytdlp_wheel_release,
)


def test_extract_latest_ytdlp_wheel_release_returns_py3_wheel() -> None:
    release = extract_latest_ytdlp_wheel_release(
        payload={
            "info": {"version": "2026.6.9"},
            "urls": [
                {
                    "packagetype": "sdist",
                    "filename": "yt_dlp-2026.6.9.tar.gz",
                    "url": "https://example.test/yt_dlp.tar.gz",
                },
                {
                    "packagetype": "bdist_wheel",
                    "filename": "yt_dlp-2026.6.9-py3-none-any.whl",
                    "url": "https://example.test/yt_dlp.whl",
                    "size": 123,
                },
            ],
        }
    )

    assert release.version == "2026.6.9"
    assert release.filename == "yt_dlp-2026.6.9-py3-none-any.whl"
    assert release.url == "https://example.test/yt_dlp.whl"
    assert release.size_bytes == 123


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"info": {}, "urls": []},
        {"info": {"version": "2026.6.9"}, "urls": []},
        {"info": {"version": "2026.6.9"}, "urls": "broken"},
    ],
)
def test_extract_latest_ytdlp_wheel_release_rejects_invalid_payload(
    payload: object,
) -> None:
    with pytest.raises(YtDlpRuntimeInstallationError):
        extract_latest_ytdlp_wheel_release(payload=payload)


def test_are_ytdlp_versions_equivalent_accepts_zero_padded_release_parts() -> None:
    assert (
        are_ytdlp_versions_equivalent(
            left_version="2026.06.09",
            right_version="2026.6.9",
        )
        is True
    )


def test_are_ytdlp_versions_equivalent_rejects_different_versions() -> None:
    assert (
        are_ytdlp_versions_equivalent(
            left_version="2026.06.10",
            right_version="2026.6.9",
        )
        is False
    )
