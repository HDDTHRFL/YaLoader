from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from yaloader.application.dto.prepared_download import PreparedDownload
from yaloader.application.ports.downloader import CancellationToken
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, OutputFormat
from yaloader.domain.source_platform import SourcePlatform, detect_source_platform
from yaloader.infrastructure.vk_audio.client import (
    VkAudioClient,
    VkAudioDirectMedia,
    VkAudioId,
    format_track_title,
    parse_vk_audio_id,
)

VK_AUDIO_RAW_INFO_KIND: Final = "vk_audio"
VK_AUDIO_RAW_INFO_KIND_KEY: Final = "kind"
VK_AUDIO_RAW_INFO_DIRECT_URL_KEY: Final = "direct_url"
VK_AUDIO_RAW_INFO_TITLE_KEY: Final = "title"
VK_AUDIO_RAW_INFO_ARTIST_KEY: Final = "artist"
VK_AUDIO_RAW_INFO_DURATION_SECONDS_KEY: Final = "duration_seconds"

VK_AUDIO_OUTPUT_FORMATS: Final[frozenset[OutputFormat]] = frozenset(
    {
        OutputFormat.MP3,
        OutputFormat.M4A,
    }
)


class VkAudioDownloadCancelledError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class VkAudioDownloadPreparer:
    client: VkAudioClient

    def prepare(
        self,
        task: DownloadTask,
        cancellation_token: CancellationToken | None = None,
    ) -> PreparedDownload:
        raise_if_cancel_requested(cancellation_token=cancellation_token)
        validate_vk_audio_task(task=task)

        media = self.client.resolve_direct_media(url=task.url.value)
        raise_if_cancel_requested(cancellation_token=cancellation_token)

        return PreparedDownload(
            task_id=task.task_id,
            url=task.url.value,
            title=format_track_title(artist=media.artist, title=media.title),
            duration_seconds=media.duration_seconds,
            raw_info=build_vk_audio_raw_info(media=media),
        )


def validate_vk_audio_task(*, task: DownloadTask) -> None:
    if detect_source_platform(url=task.url.value) is not SourcePlatform.VK_AUDIO:
        raise ValueError("Task is not a VK Audio URL.")

    if task.mode is not DownloadMode.AUDIO:
        raise ValueError("VK Audio поддерживает только режим аудио.")

    if task.output_format not in VK_AUDIO_OUTPUT_FORMATS:
        supported_formats = ", ".join(sorted(output_format.value for output_format in VK_AUDIO_OUTPUT_FORMATS))
        raise ValueError(f"VK Audio поддерживает только форматы: {supported_formats}.")


def build_vk_audio_raw_info(*, media: VkAudioDirectMedia) -> dict[str, object]:
    raw_info: dict[str, object] = {
        VK_AUDIO_RAW_INFO_KIND_KEY: VK_AUDIO_RAW_INFO_KIND,
        VK_AUDIO_RAW_INFO_DIRECT_URL_KEY: media.direct_url,
    }

    if media.title is not None:
        raw_info[VK_AUDIO_RAW_INFO_TITLE_KEY] = media.title

    if media.artist is not None:
        raw_info[VK_AUDIO_RAW_INFO_ARTIST_KEY] = media.artist

    if media.duration_seconds is not None:
        raw_info[VK_AUDIO_RAW_INFO_DURATION_SECONDS_KEY] = media.duration_seconds

    return raw_info


def is_vk_audio_raw_info(*, raw_info: Mapping[str, object]) -> bool:
    return raw_info.get(VK_AUDIO_RAW_INFO_KIND_KEY) == VK_AUDIO_RAW_INFO_KIND and isinstance(
        raw_info.get(VK_AUDIO_RAW_INFO_DIRECT_URL_KEY), str
    )


def restore_vk_audio_media_from_raw_info(
    *,
    raw_info: Mapping[str, object],
    fallback_audio_id: VkAudioId,
) -> VkAudioDirectMedia | None:
    if raw_info.get(VK_AUDIO_RAW_INFO_KIND_KEY) != VK_AUDIO_RAW_INFO_KIND:
        return None

    direct_url = raw_info.get(VK_AUDIO_RAW_INFO_DIRECT_URL_KEY)

    if not isinstance(direct_url, str) or not direct_url.strip():
        return None

    title = normalize_optional_raw_text(value=raw_info.get(VK_AUDIO_RAW_INFO_TITLE_KEY))
    artist = normalize_optional_raw_text(value=raw_info.get(VK_AUDIO_RAW_INFO_ARTIST_KEY))
    duration_seconds = normalize_optional_raw_int(value=raw_info.get(VK_AUDIO_RAW_INFO_DURATION_SECONDS_KEY))

    return VkAudioDirectMedia(
        audio_id=fallback_audio_id,
        direct_url=direct_url,
        title=title,
        artist=artist,
        duration_seconds=duration_seconds,
    )


def normalize_optional_raw_text(*, value: object) -> str | None:
    if not isinstance(value, str):
        return None

    normalized_value = value.strip()

    if not normalized_value:
        return None

    return normalized_value


def normalize_optional_raw_int(*, value: object) -> int | None:
    if isinstance(value, int) and value >= 0:
        return value

    return None


def build_vk_audio_media_from_task_url_and_raw_info(
    *,
    task: DownloadTask,
    raw_info: Mapping[str, object],
) -> VkAudioDirectMedia | None:
    return restore_vk_audio_media_from_raw_info(
        raw_info=raw_info,
        fallback_audio_id=parse_vk_audio_id(url=task.url.value),
    )


def raise_if_cancel_requested(*, cancellation_token: CancellationToken | None) -> None:
    if cancellation_token is not None and cancellation_token.is_cancel_requested:
        raise VkAudioDownloadCancelledError
