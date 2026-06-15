from __future__ import annotations

import pytest

from yaloader.domain.source_policy import is_vk_video_url, validate_supported_media_url


@pytest.mark.parametrize(
    "url",
    [
        "https://vkvideo.ru/video-123456789_456239017",
        "https://www.vkvideo.ru/video-123456789_456239017",
        "https://m.vkvideo.ru/video-123456789_456239017",
        "https://vk.com/video-123456789_456239017",
        "https://m.vk.com/video-123456789_456239017",
        "https://vk.com/video_ext.php?oid=-123456789&id=456239017&hash=test",
    ],
)
def test_is_vk_video_url_accepts_supported_hosts(url: str) -> None:
    assert is_vk_video_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/video-123456789_456239017",
        "https://vk.com.example.org/video-123456789_456239017",
        "https://notvk.com/video-123456789_456239017",
    ],
)
def test_is_vk_video_url_rejects_unsupported_hosts(url: str) -> None:
    assert is_vk_video_url(url) is False


def test_validate_supported_media_url_returns_valid_vk_video_url() -> None:
    url = "https://vkvideo.ru/video-123456789_456239017"

    result = validate_supported_media_url(url=url)

    assert result == url
