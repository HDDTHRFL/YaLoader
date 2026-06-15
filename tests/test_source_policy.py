from __future__ import annotations

import pytest

from yaloader.domain.source_policy import is_youtube_url, validate_supported_media_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=test",
        "https://youtube.com/watch?v=test",
        "https://m.youtube.com/watch?v=test",
        "https://music.youtube.com/watch?v=test",
        "https://youtu.be/test",
    ],
)
def test_is_youtube_url_accepts_supported_hosts(url: str) -> None:
    assert is_youtube_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/video",
        "https://notyoutube.com/watch?v=test",
        "https://youtube.com.example.org/watch?v=test",
        "https://vimeo.com/123",
    ],
)
def test_is_youtube_url_rejects_unsupported_hosts(url: str) -> None:
    assert is_youtube_url(url) is False


def test_validate_supported_media_url_returns_valid_youtube_url() -> None:
    url = "https://www.youtube.com/watch?v=test"

    result = validate_supported_media_url(url=url)

    assert result == url


def test_validate_supported_media_url_rejects_unsupported_host() -> None:
    with pytest.raises(ValueError, match="Only YouTube, Rutube, VK Video and Twitch URLs"):
        validate_supported_media_url(url="https://example.com/video")
