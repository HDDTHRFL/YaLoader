from __future__ import annotations

import pytest

from yaloader.domain.source_policy import is_soundcloud_url, validate_supported_media_url


@pytest.mark.parametrize(
    "url",
    [
        "https://soundcloud.com/artist/track",
        "https://www.soundcloud.com/artist/track",
        "https://m.soundcloud.com/artist/track",
        "https://soundcloud.com/artist/sets/playlist",
        "https://on.soundcloud.com/AbCdE",
        "https://snd.sc/AbCdE",
        "https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/123",
    ],
)
def test_is_soundcloud_url_accepts_supported_hosts(url: str) -> None:
    assert is_soundcloud_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/artist/track",
        "https://soundcloud.com.example.org/artist/track",
        "https://notsoundcloud.com/artist/track",
    ],
)
def test_is_soundcloud_url_rejects_unsupported_hosts(url: str) -> None:
    assert is_soundcloud_url(url) is False


def test_validate_supported_media_url_returns_valid_soundcloud_url() -> None:
    url = "https://soundcloud.com/artist/track"

    result = validate_supported_media_url(url=url)

    assert result == url
