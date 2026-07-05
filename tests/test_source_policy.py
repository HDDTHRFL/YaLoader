from __future__ import annotations

import pytest

from yaloader.domain.source_policy import (
    is_known_source_url,
    is_vk_audio_url,
    is_youtube_url,
    validate_supported_media_url,
)


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
def test_is_youtube_url_rejects_non_youtube_hosts(url: str) -> None:
    assert is_youtube_url(url) is False


def test_known_source_url_accepts_youtube_url() -> None:
    assert is_known_source_url("https://www.youtube.com/watch?v=test") is True


def test_known_source_url_rejects_ytdlp_auto_url() -> None:
    assert is_known_source_url("https://vimeo.com/123") is False


def test_validate_supported_media_url_returns_valid_youtube_url() -> None:
    url = "https://www.youtube.com/watch?v=test"

    result = validate_supported_media_url(url=url)

    assert result == url


def test_is_vk_audio_url_accepts_public_negative_vk_audio_url() -> None:
    assert is_vk_audio_url("https://vk.com/audio-2001247451_41247451") is True


def test_validate_supported_media_url_returns_public_negative_vk_audio_url() -> None:
    url = "https://vk.com/audio-2001247451_41247451"

    result = validate_supported_media_url(url=url)

    assert result == url


def test_is_vk_audio_url_accepts_public_negative_vk_audio_url_with_access_key() -> None:
    assert is_vk_audio_url("https://vk.com/audio-2001247451_41247451_c98d766105ddecb1b3") is True


def test_validate_supported_media_url_returns_public_negative_vk_audio_url_with_access_key() -> None:
    url = "https://vk.com/audio-2001247451_41247451_c98d766105ddecb1b3"

    result = validate_supported_media_url(url=url)

    assert result == url


def test_validate_supported_media_url_returns_ytdlp_auto_http_url() -> None:
    url = "https://vimeo.com/123"

    result = validate_supported_media_url(url=url)

    assert result == url


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/video",
        "file:///C:/video.mp4",
        "not-a-url",
    ],
)
def test_validate_supported_media_url_rejects_non_http_urls(url: str) -> None:
    with pytest.raises(
        ValueError,
        match="Only YouTube, Rutube, VK Video, VK Audio, Twitch, SoundCloud",
    ):
        validate_supported_media_url(url=url)
