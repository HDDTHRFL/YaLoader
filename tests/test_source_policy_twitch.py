from __future__ import annotations

import pytest

from yaloader.domain.source_policy import is_twitch_url, validate_supported_media_url


@pytest.mark.parametrize(
    "url",
    [
        "https://twitch.tv/videos/123456789",
        "https://www.twitch.tv/videos/123456789",
        "https://m.twitch.tv/videos/123456789",
        "https://clips.twitch.tv/ModernClipSlug",
        "https://www.twitch.tv/channel/clip/ModernClipSlug",
        "https://player.twitch.tv/?video=v123456789&parent=localhost",
    ],
)
def test_is_twitch_url_accepts_supported_hosts(url: str) -> None:
    assert is_twitch_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/videos/123456789",
        "https://twitch.tv.example.org/videos/123456789",
        "https://nottwitch.tv/videos/123456789",
    ],
)
def test_is_twitch_url_rejects_unsupported_hosts(url: str) -> None:
    assert is_twitch_url(url) is False


def test_validate_supported_media_url_returns_valid_twitch_url() -> None:
    url = "https://www.twitch.tv/videos/123456789"

    result = validate_supported_media_url(url=url)

    assert result == url
