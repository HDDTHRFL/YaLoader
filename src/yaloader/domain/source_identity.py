from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import parse_qs, urlparse

from yaloader.domain.source_platform import SourcePlatform, detect_source_platform
from yaloader.domain.value_objects.media_url import MediaUrl

YOUTUBE_SHORT_HOST = "youtu.be"
YOUTUBE_VIDEO_PATH_PREFIXES = frozenset(
    {
        "shorts",
        "embed",
        "live",
    }
)

RUTUBE_VIDEO_PATH_PREFIX = "video"
RUTUBE_EMBED_PATH_PREFIX = "play"
RUTUBE_DIRECT_EMBED_PATH_PREFIX = "embed"
RUTUBE_SHORTS_PATH_PREFIX = "shorts"
RUTUBE_LIVE_PATH_PREFIX = "live"

VK_VIDEO_SEGMENT_PREFIX = "video"
VK_CLIP_SEGMENT_PREFIX = "clip"
VK_VIDEO_EXT_PATH = "/video_ext.php"


def build_media_source_key(url: str) -> str:
    media_url = MediaUrl(value=url)
    platform = detect_source_platform(url=media_url.value)

    if platform is SourcePlatform.YOUTUBE:
        return build_youtube_source_key(url=media_url.value)

    if platform is SourcePlatform.RUTUBE:
        return build_rutube_source_key(url=media_url.value)

    if platform is SourcePlatform.VK_VIDEO:
        return build_vk_video_source_key(url=media_url.value)

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


def build_rutube_source_key(url: str) -> str:
    parsed_url = urlparse(url)
    video_id = extract_rutube_video_id(path=parsed_url.path)

    if video_id is not None:
        return f"rutube:video:{video_id}"

    return f"rutube:url:{url}"


def build_vk_video_source_key(url: str) -> str:
    parsed_url = urlparse(url)
    query_values = parse_qs(parsed_url.query, keep_blank_values=False)
    video_id = extract_vk_video_id(
        path=parsed_url.path,
        query_values=query_values,
    )

    if video_id is not None:
        return f"vkvideo:video:{video_id}"

    return f"vkvideo:url:{url}"


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


def extract_rutube_video_id(*, path: str) -> str | None:
    path_parts = tuple(part for part in path.split("/") if part)

    if not path_parts:
        return None

    first_path_part = path_parts[0].casefold()

    if (
        first_path_part
        in {
            RUTUBE_VIDEO_PATH_PREFIX,
            RUTUBE_DIRECT_EMBED_PATH_PREFIX,
            RUTUBE_SHORTS_PATH_PREFIX,
        }
        and len(path_parts) >= 2
    ):
        return path_parts[1]

    if (
        first_path_part in {RUTUBE_EMBED_PATH_PREFIX, RUTUBE_LIVE_PATH_PREFIX}
        and len(path_parts) >= 3
    ):
        return path_parts[2]

    return None


def extract_vk_video_id(
    *,
    path: str,
    query_values: Mapping[str, list[str]],
) -> str | None:
    embedded_video_id = extract_vk_video_id_from_video_ext_query(
        path=path,
        query_values=query_values,
    )

    if embedded_video_id is not None:
        return embedded_video_id

    path_video_id = extract_vk_video_id_from_path(path=path)

    if path_video_id is not None:
        return path_video_id

    z_video_id = extract_vk_video_id_from_z_query(query_values=query_values)

    if z_video_id is not None:
        return z_video_id

    return None


def extract_vk_video_id_from_path(*, path: str) -> str | None:
    path_parts = tuple(part for part in path.split("/") if part)

    for path_part in path_parts:
        video_id = extract_vk_video_id_from_segment(segment=path_part)

        if video_id is not None:
            return video_id

    return None


def extract_vk_video_id_from_video_ext_query(
    *,
    path: str,
    query_values: Mapping[str, list[str]],
) -> str | None:
    normalized_path = path.rstrip("/").casefold()

    if normalized_path != VK_VIDEO_EXT_PATH:
        return None

    owner_id = get_first_query_value(query_values=query_values, name="oid")
    video_id = get_first_query_value(query_values=query_values, name="id")

    if owner_id is None or video_id is None:
        return None

    return f"{owner_id}_{video_id}"


def extract_vk_video_id_from_z_query(
    *,
    query_values: Mapping[str, list[str]],
) -> str | None:
    z_value = get_first_query_value(query_values=query_values, name="z")

    if z_value is None:
        return None

    first_z_segment = z_value.split("/", maxsplit=1)[0]

    return extract_vk_video_id_from_segment(segment=first_z_segment)


def extract_vk_video_id_from_segment(*, segment: str) -> str | None:
    normalized_segment = segment.casefold()

    for prefix in (VK_VIDEO_SEGMENT_PREFIX, VK_CLIP_SEGMENT_PREFIX):
        if not normalized_segment.startswith(prefix):
            continue

        video_id = segment[len(prefix) :].strip()

        if is_valid_vk_video_id(video_id=video_id):
            return video_id

    return None


def is_valid_vk_video_id(*, video_id: str) -> bool:
    owner_id, separator, item_id = video_id.partition("_")

    if separator != "_":
        return False

    return owner_id.removeprefix("-").isdigit() and item_id.isdigit()


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
