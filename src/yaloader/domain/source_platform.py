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

VK_AUDIO_ALLOWED_HOSTS = frozenset(
    {
        "vk.com",
        "www.vk.com",
        "m.vk.com",
        "vk.ru",
        "www.vk.ru",
        "m.vk.ru",
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

TWITCH_ALLOWED_HOSTS = frozenset(
    {
        "twitch.tv",
        "www.twitch.tv",
        "m.twitch.tv",
        "clips.twitch.tv",
        "player.twitch.tv",
    }
)

SOUNDCLOUD_ALLOWED_HOSTS = frozenset(
    {
        "soundcloud.com",
        "www.soundcloud.com",
        "m.soundcloud.com",
        "on.soundcloud.com",
        "snd.sc",
        "w.soundcloud.com",
    }
)


class SourcePlatform(StrEnum):
    YOUTUBE = "youtube"
    RUTUBE = "rutube"
    VK_VIDEO = "vkvideo"
    VK_AUDIO = "vkaudio"
    TWITCH = "twitch"
    SOUNDCLOUD = "soundcloud"
    UNKNOWN = "unknown"


KNOWN_SOURCE_PLATFORMS = frozenset(
    {
        SourcePlatform.YOUTUBE,
        SourcePlatform.RUTUBE,
        SourcePlatform.VK_VIDEO,
        SourcePlatform.VK_AUDIO,
        SourcePlatform.TWITCH,
        SourcePlatform.SOUNDCLOUD,
    }
)

SOURCE_PLATFORM_LABELS = {
    SourcePlatform.YOUTUBE: "YouTube",
    SourcePlatform.RUTUBE: "Rutube",
    SourcePlatform.VK_VIDEO: "VK Video",
    SourcePlatform.VK_AUDIO: "VK Audio",
    SourcePlatform.VK_AUDIO: "VK Audio",
    SourcePlatform.TWITCH: "Twitch",
    SourcePlatform.SOUNDCLOUD: "SoundCloud",
    SourcePlatform.UNKNOWN: "Auto",
}

SOURCE_PLATFORM_QUEUE_LABELS = {
    SourcePlatform.YOUTUBE: "YouTube",
    SourcePlatform.RUTUBE: "Rutube",
    SourcePlatform.VK_VIDEO: "VK Video",
    SourcePlatform.VK_AUDIO: "VK Audio",
    SourcePlatform.TWITCH: "Twitch",
    SourcePlatform.SOUNDCLOUD: "SoundCloud",
    SourcePlatform.UNKNOWN: "Auto",
}


def is_vk_audio_path(*, path: str) -> bool:
    normalized_path = path.strip().casefold()

    if not normalized_path.startswith("/audio"):
        return False

    audio_id_text = normalized_path.removeprefix("/audio").strip("/").split("/", maxsplit=1)[0]
    audio_id_parts = audio_id_text.split("_")

    if len(audio_id_parts) < 2:
        return False

    owner_id = audio_id_parts[0]
    audio_id = audio_id_parts[1]

    return owner_id.removeprefix("-").isdigit() and audio_id.isdigit()


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

    if normalized_host in VK_AUDIO_ALLOWED_HOSTS and is_vk_audio_path(path=parsed_url.path):
        return SourcePlatform.VK_AUDIO

    if normalized_host in VK_VIDEO_ALLOWED_HOSTS:
        return SourcePlatform.VK_VIDEO

    if normalized_host in TWITCH_ALLOWED_HOSTS:
        return SourcePlatform.TWITCH

    if normalized_host in SOUNDCLOUD_ALLOWED_HOSTS:
        return SourcePlatform.SOUNDCLOUD

    return SourcePlatform.UNKNOWN


def is_youtube_url(url: str) -> bool:
    return detect_source_platform(url=url) is SourcePlatform.YOUTUBE


def is_rutube_url(url: str) -> bool:
    return detect_source_platform(url=url) is SourcePlatform.RUTUBE


def is_vk_audio_url(url: str) -> bool:
    return detect_source_platform(url=url) is SourcePlatform.VK_AUDIO


def is_vk_video_url(url: str) -> bool:
    return detect_source_platform(url=url) is SourcePlatform.VK_VIDEO


def is_twitch_url(url: str) -> bool:
    return detect_source_platform(url=url) is SourcePlatform.TWITCH


def is_soundcloud_url(url: str) -> bool:
    return detect_source_platform(url=url) is SourcePlatform.SOUNDCLOUD


def is_known_source_platform(*, platform: SourcePlatform) -> bool:
    return platform in KNOWN_SOURCE_PLATFORMS


def is_known_source_url(url: str) -> bool:
    return is_known_source_platform(platform=detect_source_platform(url=url))


def is_supported_source_url(url: str) -> bool:
    return is_http_source_url(url=url)


def is_http_source_url(*, url: str) -> bool:
    parsed_url = urlparse(url.strip())

    if parsed_url.scheme not in {"http", "https"}:
        return False

    return bool(parsed_url.netloc)


def get_source_platform_label(*, platform: SourcePlatform) -> str:
    return SOURCE_PLATFORM_LABELS[platform]


def get_source_platform_queue_label(*, platform: SourcePlatform) -> str:
    return SOURCE_PLATFORM_QUEUE_LABELS[platform]
