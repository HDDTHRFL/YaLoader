from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import parse_qs, urlparse

from yaloader.domain.source_policy import is_youtube_url
from yaloader.domain.value_objects.media_url import MediaUrl

YOUTUBE_SHORT_HOST = "youtu.be"
YOUTUBE_VIDEO_PATH_PREFIXES = frozenset(
    {
        "shorts",
        "embed",
        "live",
    }
)


def build_media_source_key(url: str) -> str:
    media_url = MediaUrl(value=url)

    if is_youtube_url(media_url.value):
        return build_youtube_source_key(url=media_url.value)

    return media_url.value


def build_youtube_source_key(url: str) -> str:
    parsed_url = urlparse(url)
    query_values = parse_qs(parsed_url.query, keep_blank_values=False)
    host = parsed_url.hostname.casefold() if parsed_url.hostname is not None else ""

    video_id = extract_youtube_video_id(
        host=host,
        path=parsed_url.path,
        query_values=query_values,
    )

    if video_id is not None:
        return f"youtube:video:{video_id}"

    playlist_id = get_first_query_value(
        query_values=query_values,
        name="list",
    )

    if playlist_id is not None:
        return f"youtube:playlist:{playlist_id}"

    return f"youtube:url:{url}"


def extract_youtube_video_id(
    *,
    host: str,
    path: str,
    query_values: Mapping[str, list[str]],
) -> str | None:
    watch_video_id = get_first_query_value(
        query_values=query_values,
        name="v",
    )

    if watch_video_id is not None:
        return watch_video_id

    path_parts = tuple(part for part in path.split("/") if part)

    if not path_parts:
        return None

    if host == YOUTUBE_SHORT_HOST:
        return path_parts[0]

    if path_parts[0] in YOUTUBE_VIDEO_PATH_PREFIXES and len(path_parts) >= 2:
        return path_parts[1]

    return None


def get_first_query_value(
    *,
    query_values: Mapping[str, list[str]],
    name: str,
) -> str | None:
    values = query_values.get(name)

    if values is None:
        return None

    for value in values:
        stripped_value = value.strip()

        if stripped_value:
            return stripped_value

    return None
