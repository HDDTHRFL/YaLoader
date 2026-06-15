from __future__ import annotations

from yaloader.domain.source_platform import (
    RUTUBE_ALLOWED_HOSTS,
    TWITCH_ALLOWED_HOSTS,
    VK_VIDEO_ALLOWED_HOSTS,
    YOUTUBE_ALLOWED_HOSTS,
    is_rutube_url,
    is_supported_source_url,
    is_twitch_url,
    is_vk_video_url,
    is_youtube_url,
)

SUPPORTED_SOURCE_NAMES_TEXT = "YouTube, Rutube, VK Video and Twitch"


def validate_supported_media_url(url: str) -> str:
    if is_supported_source_url(url):
        return url

    message = f"Only {SUPPORTED_SOURCE_NAMES_TEXT} URLs are currently supported."
    raise ValueError(message)


__all__ = (
    "RUTUBE_ALLOWED_HOSTS",
    "TWITCH_ALLOWED_HOSTS",
    "VK_VIDEO_ALLOWED_HOSTS",
    "YOUTUBE_ALLOWED_HOSTS",
    "is_rutube_url",
    "is_supported_source_url",
    "is_twitch_url",
    "is_vk_video_url",
    "is_youtube_url",
    "validate_supported_media_url",
)
