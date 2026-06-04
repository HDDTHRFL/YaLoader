from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import parse_qs, urlparse

from yaloader.domain.source_policy import is_youtube_url

YOUTUBE_PLAYLIST_PATH = "/playlist"


def should_include_playlist_for_url(*, url: str) -> bool:
    normalized_url = url.strip()

    if not normalized_url:
        return False

    if not is_youtube_url(normalized_url):
        return False

    parsed_url = urlparse(normalized_url)
    normalized_path = parsed_url.path.rstrip("/").casefold()

    if normalized_path != YOUTUBE_PLAYLIST_PATH:
        return False

    query_values = parse_qs(parsed_url.query, keep_blank_values=False)

    return get_first_query_value(query_values=query_values, name="list") is not None


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
