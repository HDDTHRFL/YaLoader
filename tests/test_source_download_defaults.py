from __future__ import annotations

import pytest

from yaloader.domain.enums import OutputFormat
from yaloader.domain.source_download_defaults import (
    DEFAULT_AUDIO_ONLY_OUTPUT_FORMAT,
    DEFAULT_VIDEO_OUTPUT_FORMAT,
    is_audio_only_source_url,
    is_video_capable_source_url,
    resolve_default_output_format_for_source_url,
    resolve_output_format_for_source_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://soundcloud.com/artist/track",
        "https://soundcloud.com/artist/sets/playlist",
        "https://on.soundcloud.com/AbCdE",
        "https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/123",
    ],
)
def test_is_audio_only_source_url_accepts_soundcloud(url: str) -> None:
    assert is_audio_only_source_url(url=url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=test",
        "https://rutube.ru/video/1234567890abcdef/",
        "https://www.twitch.tv/videos/123456789",
        "https://vkvideo.ru/video-123456789_456239017",
        "https://example.com/media",
    ],
)
def test_is_audio_only_source_url_rejects_non_audio_only_sources(url: str) -> None:
    assert is_audio_only_source_url(url=url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=test",
        "https://rutube.ru/video/1234567890abcdef/",
        "https://www.twitch.tv/videos/123456789",
        "https://vkvideo.ru/video-123456789_456239017",
    ],
)
def test_is_video_capable_source_url_accepts_video_sources(url: str) -> None:
    assert is_video_capable_source_url(url=url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://soundcloud.com/artist/track",
        "https://example.com/media",
    ],
)
def test_is_video_capable_source_url_rejects_non_video_sources(url: str) -> None:
    assert is_video_capable_source_url(url=url) is False


@pytest.mark.parametrize(
    "selected_output_format",
    [
        OutputFormat.MP4,
        OutputFormat.WEBM,
    ],
)
def test_resolve_output_format_uses_mp3_for_soundcloud_video_format(
    selected_output_format: OutputFormat,
) -> None:
    assert (
        resolve_output_format_for_source_url(
            url="https://soundcloud.com/artist/track",
            selected_output_format=selected_output_format,
        )
        is DEFAULT_AUDIO_ONLY_OUTPUT_FORMAT
    )


@pytest.mark.parametrize(
    "selected_output_format",
    [
        OutputFormat.MP3,
        OutputFormat.M4A,
    ],
)
def test_resolve_output_format_keeps_explicit_audio_format_for_soundcloud(
    selected_output_format: OutputFormat,
) -> None:
    assert (
        resolve_output_format_for_source_url(
            url="https://soundcloud.com/artist/track",
            selected_output_format=selected_output_format,
        )
        is selected_output_format
    )


def test_resolve_output_format_keeps_audio_format_for_youtube() -> None:
    assert (
        resolve_output_format_for_source_url(
            url="https://www.youtube.com/watch?v=test",
            selected_output_format=OutputFormat.MP3,
        )
        is OutputFormat.MP3
    )


@pytest.mark.parametrize(
    "selected_output_format",
    [
        OutputFormat.MP3,
        OutputFormat.M4A,
    ],
)
def test_resolve_default_output_format_uses_mp4_for_video_source_audio_format(
    selected_output_format: OutputFormat,
) -> None:
    assert (
        resolve_default_output_format_for_source_url(
            url="https://www.youtube.com/watch?v=test",
            selected_output_format=selected_output_format,
        )
        is DEFAULT_VIDEO_OUTPUT_FORMAT
    )


@pytest.mark.parametrize(
    "selected_output_format",
    [
        OutputFormat.MP4,
        OutputFormat.WEBM,
    ],
)
def test_resolve_default_output_format_keeps_video_format_for_video_source(
    selected_output_format: OutputFormat,
) -> None:
    assert (
        resolve_default_output_format_for_source_url(
            url="https://www.youtube.com/watch?v=test",
            selected_output_format=selected_output_format,
        )
        is selected_output_format
    )


def test_resolve_default_output_format_uses_mp3_for_soundcloud_video_format() -> None:
    assert (
        resolve_default_output_format_for_source_url(
            url="https://soundcloud.com/artist/track",
            selected_output_format=OutputFormat.MP4,
        )
        is DEFAULT_AUDIO_ONLY_OUTPUT_FORMAT
    )


def test_resolve_default_output_format_keeps_audio_format_for_soundcloud() -> None:
    assert (
        resolve_default_output_format_for_source_url(
            url="https://soundcloud.com/artist/track",
            selected_output_format=OutputFormat.M4A,
        )
        is OutputFormat.M4A
    )


def test_resolve_default_output_format_keeps_selected_format_for_unknown_source() -> None:
    assert (
        resolve_default_output_format_for_source_url(
            url="https://example.com/media",
            selected_output_format=OutputFormat.MP3,
        )
        is OutputFormat.MP3
    )


def test_is_audio_only_source_url_accepts_vk_audio() -> None:
    assert is_audio_only_source_url(url="https://vk.com/audio133993362_456242612_cb6b8410a741a6993a") is True


def test_is_video_capable_source_url_rejects_vk_audio() -> None:
    assert is_video_capable_source_url(url="https://vk.com/audio133993362_456242612_cb6b8410a741a6993a") is False


def test_resolve_default_output_format_uses_mp3_for_vk_audio_video_format() -> None:
    assert (
        resolve_default_output_format_for_source_url(
            url="https://vk.com/audio133993362_456242612_cb6b8410a741a6993a",
            selected_output_format=OutputFormat.MP4,
        )
        is DEFAULT_AUDIO_ONLY_OUTPUT_FORMAT
    )
