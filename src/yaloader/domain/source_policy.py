from __future__ import annotations

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


def is_youtube_url(url: str) -> bool:
    parsed_url = urlparse(url)
    host = parsed_url.hostname

    if host is None:
        return False

    return host.casefold() in YOUTUBE_ALLOWED_HOSTS


def validate_supported_media_url(url: str) -> str:
    if is_youtube_url(url):
        return url

    message = "Only YouTube URLs are currently supported."
    raise ValueError(message)
