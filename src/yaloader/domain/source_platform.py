from __future__ import annotations

from enum import StrEnum
from urllib.parse import urlparse

YOUTUBE_ALLOWED_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
    }
)

RUTUBE_ALLOWED_HOSTS = frozenset(
    {
        "rutube.ru",
        "www.rutube.ru",
        "m.rutube.ru",
    }
)

VK_VIDEO_ALLOWED_HOSTS = frozenset(
    {
        "vk.com",
        "www.vk.com",
        "m.vk.com",
        "vk.ru",
        "www.vk.ru",
        "m.vk.ru",
        "vkvideo.ru",
        "www.vkvideo.ru",
        "m.vkvideo.ru",
    }
)


class SourcePlatform(StrEnum):
    YOUTUBE = "youtube"
    RUTUBE = "rutube"
    VK_VIDEO = "vkvideo"
    UNKNOWN = "unknown"


SOURCE_PLATFORM_LABELS = {
    SourcePlatform.YOUTUBE: "YouTube",
    SourcePlatform.RUTUBE: "Rutube",
    SourcePlatform.VK_VIDEO: "VK Video",
    SourcePlatform.UNKNOWN: "Unknown",
}

SOURCE_PLATFORM_QUEUE_LABELS = {
    SourcePlatform.YOUTUBE: "YouTube",
    SourcePlatform.RUTUBE: "Rutube",
    SourcePlatform.VK_VIDEO: "VK Video",
    SourcePlatform.UNKNOWN: "Unknown",
}


def detect_source_platform(*, url: str) -> SourcePlatform:
    parsed_url = urlparse(url.strip())
    host = parsed_url.hostname

    if host is None:
        return SourcePlatform.UNKNOWN

    normalized_host = host.casefold()

    if normalized_host in YOUTUBE_ALLOWED_HOSTS:
        return SourcePlatform.YOUTUBE

    if normalized_host in RUTUBE_ALLOWED_HOSTS:
        return SourcePlatform.RUTUBE

    if normalized_host in VK_VIDEO_ALLOWED_HOSTS:
        return SourcePlatform.VK_VIDEO

    return SourcePlatform.UNKNOWN


def is_youtube_url(url: str) -> bool:
    return detect_source_platform(url=url) is SourcePlatform.YOUTUBE


def is_rutube_url(url: str) -> bool:
    return detect_source_platform(url=url) is SourcePlatform.RUTUBE


def is_vk_video_url(url: str) -> bool:
    return detect_source_platform(url=url) is SourcePlatform.VK_VIDEO


def is_supported_source_url(url: str) -> bool:
    return detect_source_platform(url=url) in {
        SourcePlatform.YOUTUBE,
        SourcePlatform.RUTUBE,
        SourcePlatform.VK_VIDEO,
    }


def get_source_platform_label(*, platform: SourcePlatform) -> str:
    return SOURCE_PLATFORM_LABELS[platform]


def get_source_platform_queue_label(*, platform: SourcePlatform) -> str:
    return SOURCE_PLATFORM_QUEUE_LABELS[platform]
