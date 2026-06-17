from __future__ import annotations

from yaloader.domain.source_platform import (
    SourcePlatform,
    detect_source_platform,
    is_supported_source_url,
)


def test_detect_source_platform_for_youtube() -> None:
    assert (
        detect_source_platform(url="https://www.youtube.com/watch?v=test") is SourcePlatform.YOUTUBE
    )


def test_detect_source_platform_for_rutube() -> None:
    assert (
        detect_source_platform(url="https://rutube.ru/video/1234567890abcdef/")
        is SourcePlatform.RUTUBE
    )


def test_detect_source_platform_for_vk_video() -> None:
    assert (
        detect_source_platform(url="https://vkvideo.ru/video-123456789_456239017")
        is SourcePlatform.VK_VIDEO
    )


def test_detect_source_platform_for_vk_video_on_vk_host() -> None:
    assert (
        detect_source_platform(url="https://vk.com/video-123456789_456239017")
        is SourcePlatform.VK_VIDEO
    )


def test_detect_source_platform_for_twitch() -> None:
    assert (
        detect_source_platform(url="https://www.twitch.tv/videos/123456789")
        is SourcePlatform.TWITCH
    )


def test_detect_source_platform_for_twitch_clips() -> None:
    assert (
        detect_source_platform(url="https://clips.twitch.tv/ModernClipSlug")
        is SourcePlatform.TWITCH
    )


def test_detect_source_platform_for_soundcloud() -> None:
    assert (
        detect_source_platform(url="https://soundcloud.com/artist/track")
        is SourcePlatform.SOUNDCLOUD
    )


def test_detect_source_platform_for_soundcloud_short_link() -> None:
    assert (
        detect_source_platform(url="https://on.soundcloud.com/AbCdE") is SourcePlatform.SOUNDCLOUD
    )


def test_rutube_is_supported_source_url() -> None:
    assert is_supported_source_url(url="https://rutube.ru/video/1234567890abcdef/")


def test_vk_video_is_supported_source_url() -> None:
    assert is_supported_source_url(url="https://vkvideo.ru/video-123456789_456239017")


def test_twitch_is_supported_source_url() -> None:
    assert is_supported_source_url(url="https://www.twitch.tv/videos/123456789")


def test_soundcloud_is_supported_source_url() -> None:
    assert is_supported_source_url(url="https://soundcloud.com/artist/track")
