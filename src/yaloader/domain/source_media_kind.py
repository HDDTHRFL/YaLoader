from __future__ import annotations

from enum import StrEnum
from urllib.parse import urlparse

from yaloader.domain.source_policy import is_youtube_url

YOUTUBE_SHORTS_PATH_PREFIX = "/shorts/"


class SourceMediaKind(StrEnum):
    VIDEO = "video"
    SHORTS = "shorts"
    PLAYLIST = "playlist"


def detect_source_media_kind(
    *,
    url: str,
    include_playlist: bool,
) -> SourceMediaKind:
    if include_playlist:
        return SourceMediaKind.PLAYLIST

    if is_youtube_shorts_url(url=url):
        return SourceMediaKind.SHORTS

    return SourceMediaKind.VIDEO


def is_youtube_shorts_url(*, url: str) -> bool:
    normalized_url = url.strip()

    if not normalized_url:
        return False

    if not is_youtube_url(normalized_url):
        return False

    parsed_url = urlparse(normalized_url)
    normalized_path = parsed_url.path.casefold()

    return normalized_path.startswith(YOUTUBE_SHORTS_PATH_PREFIX)
