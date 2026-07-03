from __future__ import annotations

import argparse
import base64
import html as html_tools
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Final
from urllib.parse import parse_qs, urlparse

import httpx

VK_DESKTOP_AUDIO_RELOAD_URL: Final = "https://vk.com/al_audio.php?act=reload_audio"
VK_MOBILE_AUDIO_RELOAD_URLS: Final = (
    "https://m.vk.com/audio",
    "https://m.vk.ru/audio",
)
VK_AUDIO_URL_RE: Final = re.compile(
    r"^/audio(?P<owner_id>-?\d+)_(?P<audio_id>\d+)(?:_(?P<access_key>[A-Za-z0-9]+))?/?$"
)
EMBEDDED_URL_RE: Final = re.compile(r"(?:https?:)?\\?/\\?/[^\s\"'<>]+")
DATA_AUDIO_ATTRIBUTE_RE: Final = re.compile(
    r"data-audio=(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
    re.DOTALL,
)
DATA_AUDIO_ENTITY_ATTRIBUTE_RE: Final = re.compile(
    r"data-audio=&quot;(?P<value>.*?)&quot;",
    re.DOTALL,
)
M3U8_TO_MP3_RE: Final = re.compile(r"/[0-9a-f]+(/audios)?/([0-9a-f]+)/index\.m3u8")
SUPPORTED_AUDIO_MEDIA_EXTENSIONS: Final = frozenset({".mp3", ".m4a", ".aac", ".ogg", ".opus", ".m3u8"})
REJECTED_MEDIA_HOSTS: Final = frozenset(
    {
        "com.vkontakte.android",
        "vk.com",
        "www.vk.com",
        "m.vk.com",
        "vk.ru",
        "www.vk.ru",
        "m.vk.ru",
        "login.vk.com",
        "id.vk.com",
        "api.vk.com",
        "web.api.vk.com",
        "st1-93.vk.com",
        "stats.vk-portal.net",
        "vk-portal.net",
    }
)
DEFAULT_HTTP_TIMEOUT_SECONDS: Final = 20.0
DOWNLOAD_CHUNK_SIZE_BYTES: Final = 1024 * 1024
FALLBACK_AUDIO_EXTENSION: Final = ".mp3"
DEFAULT_AUDIO_OUTPUT_FORMAT: Final = "mp3"
VK_AUDIO_OUTPUT_FORMATS: Final = ("mp3", "m4a")
FFMPEG_EXECUTABLE_NAME: Final = "ffmpeg"
FFMPEG_WINDOWS_EXECUTABLE_NAME: Final = "ffmpeg.exe"
FFMPEG_DOWNLOAD_TIMEOUT_SECONDS: Final = 900
RESPONSE_PREVIEW_LENGTH: Final = 220
MIN_AUDIO_HASH_PARTS_COUNT: Final = 6
VK_AUDIO_OBFUSCATION_ALPHABET: Final = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN0PQRSTUVWXYZO123456789+/="
STANDARD_BASE64_ALPHABET: Final = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
VK_AUDIO_OPERATION_SEPARATOR: Final = "\t"
VK_AUDIO_OPERATION_ARGUMENT_SEPARATOR: Final = "\v"

VK_AUDIO_REQUEST_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Origin": "https://vk.com",
    "Referer": "https://vk.com/",
    "X-Requested-With": "XMLHttpRequest",
}

VK_MOBILE_AUDIO_REQUEST_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "*/*",
    "Origin": "https://m.vk.com",
    "Referer": "https://m.vk.com/audio",
    "X-Requested-With": "XMLHttpRequest",
}

VK_AUDIO_DEFAULT_COOKIES: Final[dict[str, str]] = {
    "remixaudio_show_alert_today": "0",
    "remixmdevice": "1920/1080/2/!!-!!!!",
}


class VkAudioProbeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class VkAudioId:
    owner_id: str
    audio_id: str
    access_key: str | None = None

    @property
    def value(self) -> str:
        if self.access_key is None:
            return f"{self.owner_id}_{self.audio_id}"

        return f"{self.owner_id}_{self.audio_id}_{self.access_key}"

    @property
    def base_value(self) -> str:
        return f"{self.owner_id}_{self.audio_id}"

    @property
    def display_value(self) -> str:
        if self.access_key is None:
            return self.value

        return f"{self.owner_id}_{self.audio_id}_<access-key>"

    @property
    def safe_file_stem(self) -> str:
        return f"vk_audio_{self.owner_id}_{self.audio_id}"


@dataclass(frozen=True, slots=True)
class VkAudioTrack:
    owner_id: str
    audio_id: str
    title: str | None = None
    artist: str | None = None
    duration_seconds: int | None = None
    direct_url: str | None = None
    action_hash: str | None = None
    url_hash: str | None = None
    playback_hash: str | None = None
    access_key: str | None = None
    source_owner_id: str | None = None
    source_audio_id: str | None = None
    user_id: int | None = None

    @property
    def base_id(self) -> str:
        return f"{self.owner_id}_{self.audio_id}"

    @property
    def source_id(self) -> str | None:
        if self.source_owner_id is None or self.source_audio_id is None:
            return None

        return f"{self.source_owner_id}_{self.source_audio_id}"

    @property
    def full_id(self) -> str | None:
        candidates = build_full_id_candidates(track=self)

        if not candidates:
            return None

        return candidates[0]

    def matches(self, audio_id: VkAudioId) -> bool:
        if self.owner_id == audio_id.owner_id and self.audio_id == audio_id.audio_id:
            return True

        return self.source_owner_id == audio_id.owner_id and self.source_audio_id == audio_id.audio_id


@dataclass(frozen=True, slots=True)
class VkAudioDirectMedia:
    audio_id: VkAudioId
    direct_url: str
    title: str | None = None
    artist: str | None = None
    duration_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class VkResponseDiagnostics:
    source: str
    length: int
    strings_count: int
    embedded_url_candidates_count: int
    has_bad_hash: bool
    has_audio_api_unavailable: bool
    has_payload_marker: bool
    has_login_marker: bool
    safe_preview: str

    def format_for_error(self) -> str:
        return (
            f"{self.source}: length={self.length}, strings={self.strings_count}, "
            f"url_candidates={self.embedded_url_candidates_count}, bad_hash={self.has_bad_hash}, "
            f"audio_api_unavailable={self.has_audio_api_unavailable}, "
            f"payload_marker={self.has_payload_marker}, login_marker={self.has_login_marker}, "
            f"preview={self.safe_preview!r}"
        )


class VkAudioDataHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.audio_data_values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collect_audio_data(attrs=attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collect_audio_data(attrs=attrs)

    def _collect_audio_data(self, *, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name != "data-audio" or value is None:
                continue

            self.audio_data_values.append(value)


def main(argv: Sequence[str] | None = None) -> int:
    parsed_args = parse_args(argv=argv)

    try:
        audio_id = parse_vk_audio_id(url=parsed_args.url)
        cookies_file = resolve_cookies_file(cookies_file=parsed_args.cookies_file)
        media = resolve_vk_audio_direct_media(
            url=parsed_args.url,
            cookies_file=cookies_file,
            timeout_seconds=parsed_args.timeout,
            dump_response_file=parsed_args.dump_response_file,
        )
    except VkAudioProbeError as error:
        sys.stderr.write(f"VK Audio probe failed: {error}\n")
        return 1

    sys.stdout.write("VK Audio direct media resolved.\n")
    sys.stdout.write(f"Audio id:      {audio_id.display_value}\n")
    sys.stdout.write(f"Cookies file:  {cookies_file}\n")

    if media.artist is not None or media.title is not None:
        sys.stdout.write(f"Track:         {format_track_title(artist=media.artist, title=media.title)}\n")

    if media.duration_seconds is not None:
        sys.stdout.write(f"Duration:      {media.duration_seconds} sec\n")

    sys.stdout.write(f"Direct media:  {redact_url_query(url=media.direct_url)}\n")

    if parsed_args.download_dir is None:
        return 0

    try:
        output_path = download_direct_audio(
            media=media,
            download_dir=parsed_args.download_dir.resolve(),
            timeout_seconds=parsed_args.timeout,
            output_format=parsed_args.output_format,
            ffmpeg_path=parsed_args.ffmpeg_path,
        )
    except VkAudioProbeError as error:
        sys.stderr.write(f"VK Audio download failed: {error}\n")
        return 1

    sys.stdout.write(f"Downloaded:    {output_path}\n")
    return 0


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Experimental VK Audio direct URL probe for YaLoader development.",
    )
    parser.add_argument(
        "url",
        help="VK Audio URL, for example https://vk.com/audio-2001247452_41247452.",
    )
    parser.add_argument(
        "--cookies-file",
        type=Path,
        default=None,
        help="Path to Netscape cookies.txt. Defaults to %%APPDATA%%\\yaloader\\cookies.txt.",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=None,
        help="If provided, download the resolved direct audio file into this directory.",
    )
    parser.add_argument(
        "--output-format",
        choices=VK_AUDIO_OUTPUT_FORMATS,
        default=DEFAULT_AUDIO_OUTPUT_FORMAT,
        help="Output format for HLS VK Audio streams. Defaults to mp3.",
    )
    parser.add_argument(
        "--ffmpeg-path",
        type=Path,
        default=None,
        help="Explicit ffmpeg executable path for HLS VK Audio downloads.",
    )
    parser.add_argument(
        "--dump-response-file",
        type=Path,
        default=None,
        help="Write raw VK responses to a local file for manual inspection. Do not publish this file.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_HTTP_TIMEOUT_SECONDS,
        help="HTTP timeout in seconds.",
    )

    return parser.parse_args(argv)


def resolve_vk_audio_direct_media(
    *,
    url: str,
    cookies_file: Path,
    timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
    dump_response_file: Path | None = None,
) -> VkAudioDirectMedia:
    audio_id = parse_vk_audio_id(url=url)
    cookies = load_vk_audio_cookies(cookies_file=cookies_file)

    response_dump_parts: list[tuple[str, str]] = []

    direct_media = resolve_from_desktop_reload_audio(
        audio_id=audio_id,
        cookies=cookies,
        timeout_seconds=timeout_seconds,
        response_dump_parts=response_dump_parts,
    )

    if direct_media is not None:
        dump_vk_responses_if_requested(
            dump_response_file=dump_response_file,
            response_dump_parts=response_dump_parts,
        )
        return direct_media

    direct_media = resolve_from_mobile_reload_audio(
        audio_id=audio_id,
        cookies=cookies,
        timeout_seconds=timeout_seconds,
        response_dump_parts=response_dump_parts,
    )

    if direct_media is not None:
        dump_vk_responses_if_requested(
            dump_response_file=dump_response_file,
            response_dump_parts=response_dump_parts,
        )
        return direct_media

    direct_media = resolve_from_mobile_load_section(
        audio_id=audio_id,
        cookies=cookies,
        timeout_seconds=timeout_seconds,
        response_dump_parts=response_dump_parts,
    )

    if direct_media is not None:
        dump_vk_responses_if_requested(
            dump_response_file=dump_response_file,
            response_dump_parts=response_dump_parts,
        )
        return direct_media

    page_tracks = collect_tracks_from_audio_pages(
        url=url,
        audio_id=audio_id,
        cookies=cookies,
        timeout_seconds=timeout_seconds,
        response_dump_parts=response_dump_parts,
    )

    direct_media = select_direct_media_from_tracks(audio_id=audio_id, tracks=page_tracks)

    if direct_media is not None:
        dump_vk_responses_if_requested(
            dump_response_file=dump_response_file,
            response_dump_parts=response_dump_parts,
        )
        return direct_media

    full_ids = collect_full_id_candidates(audio_id=audio_id, tracks=page_tracks)

    if full_ids:
        direct_media = resolve_from_mobile_reload_audio_ids(
            audio_id=audio_id,
            audio_ids=full_ids,
            cookies=cookies,
            timeout_seconds=timeout_seconds,
            response_dump_parts=response_dump_parts,
        )

        if direct_media is not None:
            dump_vk_responses_if_requested(
                dump_response_file=dump_response_file,
                response_dump_parts=response_dump_parts,
            )
            return direct_media

    dump_vk_responses_if_requested(
        dump_response_file=dump_response_file,
        response_dump_parts=response_dump_parts,
    )

    if has_audio_api_unavailable_response(response_dump_parts=response_dump_parts):
        raise VkAudioProbeError(
            "VK отдал audio_api_unavailable вместо прямой media URL. "
            "Это уже следующий уровень защиты: нужно добавить decoder для VK audio_api_unavailable."
        )

    if has_bad_hash_response(response_dump_parts=response_dump_parts):
        diagnostics_text = build_dump_response_marker_diagnostics_text(
            response_dump_parts=response_dump_parts,
        )
        raise VkAudioProbeError(
            "VK reload_audio вернул bad_hash, а мобильный fallback не нашёл полный audio hash. "
            "Нужно получить HTML-блок data-audio с actionHash/urlHash или другой рабочий источник hashes. "
            f"Диагностика: {diagnostics_text}"
        )

    diagnostics = tuple(
        build_response_diagnostics(
            source=source,
            value=response_text,
            raw_text=response_text,
        ).format_for_error()
        for source, response_text in response_dump_parts
    )

    if diagnostics:
        raise VkAudioProbeError("VK ответил, но прямой media URL не найден. Диагностика: " + " | ".join(diagnostics))

    raise VkAudioProbeError("VK Audio не удалось обработать: VK не вернул полезный ответ.")


def resolve_from_desktop_reload_audio(
    *,
    audio_id: VkAudioId,
    cookies: Mapping[str, str],
    timeout_seconds: float,
    response_dump_parts: list[tuple[str, str]],
) -> VkAudioDirectMedia | None:
    response_text = request_vk_desktop_audio_reload(
        audio_id=audio_id,
        cookies=cookies,
        timeout_seconds=timeout_seconds,
    )
    response_dump_parts.append(("desktop reload_audio", response_text))

    try:
        payload = parse_vk_al_json_payload(text=response_text)
    except VkAudioProbeError:
        return None

    direct_url = find_direct_audio_url(value=payload)

    if direct_url is None:
        return None

    return VkAudioDirectMedia(
        audio_id=audio_id,
        direct_url=direct_url,
    )


def resolve_from_mobile_reload_audio(
    *,
    audio_id: VkAudioId,
    cookies: Mapping[str, str],
    timeout_seconds: float,
    response_dump_parts: list[tuple[str, str]],
) -> VkAudioDirectMedia | None:
    audio_ids = build_initial_mobile_audio_id_candidates(audio_id=audio_id)

    return resolve_from_mobile_reload_audio_ids(
        audio_id=audio_id,
        audio_ids=audio_ids,
        cookies=cookies,
        timeout_seconds=timeout_seconds,
        response_dump_parts=response_dump_parts,
    )


def resolve_from_mobile_reload_audio_ids(
    *,
    audio_id: VkAudioId,
    audio_ids: Iterable[str],
    cookies: Mapping[str, str],
    timeout_seconds: float,
    response_dump_parts: list[tuple[str, str]],
) -> VkAudioDirectMedia | None:
    unique_audio_ids = tuple(dict.fromkeys(audio_ids))

    if not unique_audio_ids:
        return None

    audio_id_groups = build_mobile_reload_audio_id_groups(audio_ids=unique_audio_ids)

    for attempt_index, audio_id_group in enumerate(audio_id_groups, start=1):
        for reload_url in VK_MOBILE_AUDIO_RELOAD_URLS:
            response_text = request_vk_mobile_audio_reload(
                reload_url=reload_url,
                audio_ids=audio_id_group,
                cookies=cookies,
                timeout_seconds=timeout_seconds,
            )

            source = (
                f"mobile reload_audio {reload_url} "
                f"attempt={attempt_index}/{len(audio_id_groups)} ids={len(audio_id_group)}"
            )

            try:
                payload = parse_json_response(text=response_text)
            except VkAudioProbeError:
                response_dump_parts.append((f"{source} tracks=0", response_text))
                continue

            tracks = extract_audio_tracks_from_mobile_reload_payload(payload=payload)
            response_dump_parts.append(
                (
                    build_track_diagnostic_source(
                        source=source,
                        audio_id=audio_id,
                        tracks=tracks,
                    ),
                    response_text,
                )
            )
            direct_media = select_direct_media_from_tracks(audio_id=audio_id, tracks=tracks)

            if direct_media is not None:
                return direct_media

    return None


def build_mobile_reload_audio_id_groups(*, audio_ids: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    single_audio_id_groups = tuple((audio_id,) for audio_id in audio_ids)

    if len(audio_ids) <= 1:
        return single_audio_id_groups

    return (*single_audio_id_groups, audio_ids)


def build_initial_mobile_audio_id_candidates(*, audio_id: VkAudioId) -> tuple[str, ...]:
    candidates = [audio_id.base_value]

    if audio_id.access_key is not None:
        candidates.append(audio_id.value)

    return tuple(candidates)


def resolve_from_mobile_load_section(
    *,
    audio_id: VkAudioId,
    cookies: Mapping[str, str],
    timeout_seconds: float,
    response_dump_parts: list[tuple[str, str]],
) -> VkAudioDirectMedia | None:
    tracks = collect_tracks_from_mobile_load_section(
        audio_id=audio_id,
        cookies=cookies,
        timeout_seconds=timeout_seconds,
        response_dump_parts=response_dump_parts,
    )
    direct_media = select_direct_media_from_tracks(audio_id=audio_id, tracks=tracks)

    if direct_media is not None:
        return direct_media

    full_ids = collect_full_id_candidates(audio_id=audio_id, tracks=tracks)

    if not full_ids:
        return None

    return resolve_from_mobile_reload_audio_ids(
        audio_id=audio_id,
        audio_ids=full_ids,
        cookies=cookies,
        timeout_seconds=timeout_seconds,
        response_dump_parts=response_dump_parts,
    )


def collect_tracks_from_mobile_load_section(
    *,
    audio_id: VkAudioId,
    cookies: Mapping[str, str],
    timeout_seconds: float,
    response_dump_parts: list[tuple[str, str]],
) -> tuple[VkAudioTrack, ...]:
    tracks: list[VkAudioTrack] = []

    for load_section_url in VK_MOBILE_AUDIO_RELOAD_URLS:
        response_text = request_vk_mobile_audio_load_section(
            load_section_url=load_section_url,
            owner_id=audio_id.owner_id,
            cookies=cookies,
            timeout_seconds=timeout_seconds,
        )

        try:
            payload = parse_json_response(text=response_text)
        except VkAudioProbeError:
            response_dump_parts.append((f"mobile load_section {load_section_url} tracks=0", response_text))
            continue

        extracted_tracks = list(extract_audio_tracks_from_unknown_value(value=payload))

        for html_fragment in extract_load_section_html_fragments(payload=payload):
            extracted_tracks.extend(extract_audio_tracks_from_html(html_text=html_fragment))

        extracted_tracks = list(deduplicate_audio_tracks(tracks=extracted_tracks))

        response_dump_parts.append(
            (
                build_track_diagnostic_source(
                    source=f"mobile load_section {load_section_url}",
                    audio_id=audio_id,
                    tracks=extracted_tracks,
                ),
                response_text,
            )
        )
        tracks.extend(extracted_tracks)

    return tuple(deduplicate_audio_tracks(tracks=tracks))


def collect_full_id_candidates(
    *,
    audio_id: VkAudioId,
    tracks: Iterable[VkAudioTrack],
) -> tuple[str, ...]:
    candidates: list[str] = []

    for track in tracks:
        if not track.matches(audio_id):
            continue

        candidates.extend(build_full_id_candidates(track=track))

    return tuple(dict.fromkeys(candidates))


def build_full_id_candidates(*, track: VkAudioTrack) -> tuple[str, ...]:
    id_pairs: list[tuple[str, str]] = [(track.owner_id, track.audio_id)]

    if track.source_owner_id is not None and track.source_audio_id is not None:
        id_pairs.append((track.source_owner_id, track.source_audio_id))

    hash_pairs: list[tuple[str, str]] = []

    if track.action_hash is not None and track.url_hash is not None:
        hash_pairs.append((track.action_hash, track.url_hash))

    if track.playback_hash is not None and track.access_key is not None:
        hash_pairs.append((track.playback_hash, track.access_key))

    if track.action_hash is not None and track.access_key is not None:
        hash_pairs.append((track.action_hash, track.access_key))

    if track.playback_hash is not None and track.url_hash is not None:
        hash_pairs.append((track.playback_hash, track.url_hash))

    candidates = [
        f"{owner_id}_{audio_id}_{first_hash}_{second_hash}"
        for owner_id, audio_id in id_pairs
        for first_hash, second_hash in hash_pairs
        if owner_id and audio_id and first_hash and second_hash
    ]

    return tuple(dict.fromkeys(candidates))


def deduplicate_audio_tracks(*, tracks: Iterable[VkAudioTrack]) -> tuple[VkAudioTrack, ...]:
    deduplicated_tracks: list[VkAudioTrack] = []
    seen_track_keys: set[tuple[object, ...]] = set()

    for track in tracks:
        track_key = build_track_key(track=track)

        if track_key in seen_track_keys:
            continue

        seen_track_keys.add(track_key)
        deduplicated_tracks.append(track)

    return tuple(deduplicated_tracks)


def collect_tracks_from_audio_pages(
    *,
    url: str,
    audio_id: VkAudioId,
    cookies: Mapping[str, str],
    timeout_seconds: float,
    response_dump_parts: list[tuple[str, str]],
) -> tuple[VkAudioTrack, ...]:
    tracks: list[VkAudioTrack] = []

    for page_url in build_audio_page_candidates(url=url, audio_id=audio_id):
        response_text = request_vk_audio_page(
            url=page_url,
            cookies=cookies,
            timeout_seconds=timeout_seconds,
        )
        extracted_tracks = extract_audio_tracks_from_html(html_text=response_text)
        response_dump_parts.append(
            (
                build_track_diagnostic_source(
                    source=f"audio page {page_url}",
                    audio_id=audio_id,
                    tracks=extracted_tracks,
                ),
                response_text,
            )
        )
        tracks.extend(extracted_tracks)

    return tuple(tracks)


def build_audio_page_candidates(*, url: str, audio_id: VkAudioId) -> tuple[str, ...]:
    path = f"/audio{audio_id.value}"

    return tuple(
        dict.fromkeys(
            (
                url,
                f"https://m.vk.com{path}",
                f"https://m.vk.ru{path}",
                f"https://vk.com{path}",
                f"https://vk.ru{path}",
                "https://m.vk.com/audio",
                "https://m.vk.ru/audio",
            )
        )
    )


def select_direct_media_from_tracks(
    *,
    audio_id: VkAudioId,
    tracks: Iterable[VkAudioTrack],
) -> VkAudioDirectMedia | None:
    for track in tracks:
        if not track.matches(audio_id):
            continue

        if track.direct_url is None:
            continue

        direct_url = normalize_direct_audio_url_candidate(value=track.direct_url)

        if direct_url is None:
            continue

        direct_url = convert_m3u8_audio_url_to_mp3_if_possible(url=direct_url)

        return VkAudioDirectMedia(
            audio_id=audio_id,
            direct_url=direct_url,
            title=track.title,
            artist=track.artist,
            duration_seconds=track.duration_seconds,
        )

    return None


def parse_vk_audio_id(*, url: str) -> VkAudioId:
    parsed_url = urlparse(url.strip())

    if parsed_url.scheme not in {"http", "https"}:
        raise VkAudioProbeError("VK Audio URL должен использовать http или https.")

    host = parsed_url.hostname.casefold() if parsed_url.hostname is not None else ""

    if host not in {"vk.com", "www.vk.com", "m.vk.com", "vk.ru", "www.vk.ru", "m.vk.ru"}:
        raise VkAudioProbeError(f"неподдерживаемый VK Audio host: {host or '<empty>'}")

    match = VK_AUDIO_URL_RE.fullmatch(parsed_url.path)

    if match is None:
        raise VkAudioProbeError("URL не похож на VK Audio ссылку вида https://vk.com/audio-123_456.")

    return VkAudioId(
        owner_id=match.group("owner_id"),
        audio_id=match.group("audio_id"),
        access_key=match.group("access_key"),
    )


def resolve_cookies_file(*, cookies_file: Path | None) -> Path:
    if cookies_file is not None:
        resolved_cookies_file = cookies_file.resolve()

        if not resolved_cookies_file.is_file():
            raise VkAudioProbeError(f"cookies.txt не найден: {resolved_cookies_file}")

        return resolved_cookies_file

    appdata_dir = os.getenv("APPDATA")

    if appdata_dir is None:
        raise VkAudioProbeError("APPDATA не задан. Укажи cookies.txt через --cookies-file.")

    resolved_cookies_file = Path(appdata_dir) / "yaloader" / "cookies.txt"

    if not resolved_cookies_file.is_file():
        raise VkAudioProbeError(f"cookies.txt не найден: {resolved_cookies_file}")

    return resolved_cookies_file


def load_vk_audio_cookies(*, cookies_file: Path) -> dict[str, str]:
    cookies = load_netscape_cookies(cookies_file=cookies_file)

    for name, value in VK_AUDIO_DEFAULT_COOKIES.items():
        cookies.setdefault(name, value)

    if not cookies:
        raise VkAudioProbeError(f"cookies.txt не содержит cookies для запроса VK Audio: {cookies_file}")

    return cookies


def load_netscape_cookies(*, cookies_file: Path) -> dict[str, str]:
    try:
        lines = cookies_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as error:
        raise VkAudioProbeError(f"не удалось прочитать cookies.txt: {error}") from error

    cookies: dict[str, str] = {}

    for line in lines:
        parsed_cookie = parse_netscape_cookie_line(line=line)

        if parsed_cookie is None:
            continue

        name, value = parsed_cookie
        cookies[name] = value

    return cookies


def parse_netscape_cookie_line(*, line: str) -> tuple[str, str] | None:
    normalized_line = line.strip()

    if not normalized_line or normalized_line.startswith("#"):
        return None

    fields = normalized_line.split("\t")

    if len(fields) < 7:
        fields = normalized_line.split(maxsplit=6)

    if len(fields) < 7:
        return None

    name = fields[5].strip()
    value = fields[6].strip()

    if not name:
        return None

    return name, value


def request_vk_desktop_audio_reload(
    *,
    audio_id: VkAudioId,
    cookies: Mapping[str, str],
    timeout_seconds: float,
) -> str:
    return request_text(
        url=VK_DESKTOP_AUDIO_RELOAD_URL,
        method="POST",
        cookies=cookies,
        headers=VK_AUDIO_REQUEST_HEADERS,
        timeout_seconds=timeout_seconds,
        data={
            "al": "1",
            "ids": audio_id.value,
        },
        error_context="VK desktop reload_audio",
    )


def request_vk_mobile_audio_load_section(
    *,
    load_section_url: str,
    owner_id: str,
    cookies: Mapping[str, str],
    timeout_seconds: float,
) -> str:
    return request_text(
        url=load_section_url,
        method="POST",
        cookies=cookies,
        headers=VK_MOBILE_AUDIO_REQUEST_HEADERS,
        timeout_seconds=timeout_seconds,
        data={
            "act": "load_section",
            "al": "1",
            "claim": "0",
            "owner_id": owner_id,
            "playlist_id": "-1",
            "offset": "0",
            "type": "playlist",
            "is_loading_all": "1",
        },
        error_context=f"VK mobile load_section {load_section_url}",
    )


def request_vk_mobile_audio_reload(
    *,
    reload_url: str,
    audio_ids: tuple[str, ...],
    cookies: Mapping[str, str],
    timeout_seconds: float,
) -> str:
    return request_text(
        url=reload_url,
        method="POST",
        cookies=cookies,
        headers=VK_MOBILE_AUDIO_REQUEST_HEADERS,
        timeout_seconds=timeout_seconds,
        data={
            "act": "reload_audio",
            "al": "1",
            "claim": "0",
            "from": "audio",
            "ids": ",".join(audio_ids),
        },
        error_context=f"VK mobile reload_audio {reload_url}",
    )


def request_vk_audio_page(
    *,
    url: str,
    cookies: Mapping[str, str],
    timeout_seconds: float,
) -> str:
    return request_text(
        url=url,
        method="GET",
        cookies=cookies,
        headers=VK_MOBILE_AUDIO_REQUEST_HEADERS,
        timeout_seconds=timeout_seconds,
        data=None,
        error_context=f"VK audio page {url}",
    )


def request_text(
    *,
    url: str,
    method: str,
    cookies: Mapping[str, str],
    headers: Mapping[str, str],
    timeout_seconds: float,
    data: Mapping[str, str] | None,
    error_context: str,
) -> str:
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout_seconds,
            cookies=dict(cookies),
            headers=dict(headers),
        ) as client:
            response = client.request(method, url, data=data)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as error:
        raise VkAudioProbeError(f"{error_context} вернул HTTP {error.response.status_code}") from error
    except httpx.HTTPError as error:
        raise VkAudioProbeError(f"{error_context} недоступен или запрос не выполнен: {error}") from error


def parse_vk_al_json_payload(*, text: str) -> object:
    normalized_text = text.strip()

    if normalized_text.startswith("<!--"):
        normalized_text = normalized_text.removeprefix("<!--").strip()

    json_start_index = find_first_json_start_index(text=normalized_text)

    if json_start_index is None:
        raise VkAudioProbeError("в ответе VK не найден JSON payload.")

    json_text = normalized_text[json_start_index:]

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as error:
        raise VkAudioProbeError(f"не удалось разобрать JSON payload VK: {error}") from error


def parse_json_response(*, text: str) -> object:
    normalized_text = text.strip()

    if normalized_text.startswith("<!--"):
        normalized_text = normalized_text.removeprefix("<!--").strip()

    try:
        return json.loads(normalized_text)
    except json.JSONDecodeError:
        return parse_vk_al_json_payload(text=text)


def find_first_json_start_index(*, text: str) -> int | None:
    candidates = tuple(index for index in (text.find("{"), text.find("[")) if index >= 0)

    if not candidates:
        return None

    return min(candidates)


def extract_load_section_html_fragments(*, payload: object) -> tuple[str, ...]:
    fragments: list[str] = []
    stack: list[object] = [payload]

    while stack:
        current_value = stack.pop()

        if isinstance(current_value, str):
            if is_probable_audio_html_fragment(value=current_value):
                fragments.append(current_value)

            continue

        if isinstance(current_value, Mapping):
            stack.extend(current_value.values())
            continue

        if isinstance(current_value, Sequence) and not isinstance(current_value, str | bytes):
            stack.extend(current_value)

    return tuple(fragments)


def is_probable_audio_html_fragment(*, value: str) -> bool:
    normalized_value = value.casefold()

    return (
        "data-audio" in normalized_value
        or "audio_item" in normalized_value
        or "secondaryattachment" in normalized_value
    )


def extract_audio_tracks_from_mobile_reload_payload(*, payload: object) -> tuple[VkAudioTrack, ...]:
    return extract_audio_tracks_from_unknown_value(value=payload)


def extract_audio_tracks_from_unknown_value(*, value: object) -> tuple[VkAudioTrack, ...]:
    tracks: list[VkAudioTrack] = []

    collect_audio_tracks_from_unknown_value(
        value=value,
        tracks=tracks,
    )

    return deduplicate_audio_tracks(tracks=tracks)


def collect_audio_tracks_from_unknown_value(
    *,
    value: object,
    tracks: list[VkAudioTrack],
) -> None:
    track = parse_vk_audio_track(value=value)

    if track is not None:
        tracks.append(track)

    if isinstance(value, Mapping):
        for nested_value in value.values():
            collect_audio_tracks_from_unknown_value(
                value=nested_value,
                tracks=tracks,
            )

        return

    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for nested_value in value:
            collect_audio_tracks_from_unknown_value(
                value=nested_value,
                tracks=tracks,
            )


def extract_audio_tracks_from_html(*, html_text: str) -> tuple[VkAudioTrack, ...]:
    tracks: list[VkAudioTrack] = []

    for audio_data_text in extract_audio_data_texts_from_html(html_text=html_text):
        audio_data = parse_audio_data_json(value=audio_data_text)

        if audio_data is None:
            continue

        track = parse_vk_audio_track(value=audio_data)

        if track is not None:
            tracks.append(track)

    return deduplicate_audio_tracks(tracks=tracks)


def build_track_key(*, track: VkAudioTrack) -> tuple[object, ...]:
    return (
        track.owner_id,
        track.audio_id,
        track.title,
        track.artist,
        track.duration_seconds,
        track.direct_url,
        track.action_hash,
        track.url_hash,
        track.playback_hash,
        track.access_key,
        track.source_owner_id,
        track.source_audio_id,
    )


def extract_audio_data_texts_from_html(*, html_text: str) -> tuple[str, ...]:
    parser = VkAudioDataHtmlParser()
    parser.feed(html_text)

    values: list[str] = []
    values.extend(parser.audio_data_values)
    values.extend(scan_data_audio_values(html_text=html_text))

    return tuple(dict.fromkeys(values))


def scan_data_audio_values(*, html_text: str) -> tuple[str, ...]:
    values: list[str] = []
    marker = "data-audio"
    search_start_index = 0

    while True:
        marker_index = html_text.find(marker, search_start_index)

        if marker_index < 0:
            break

        equals_index = html_text.find("=", marker_index + len(marker))

        if equals_index < 0:
            break

        value_start_index = skip_whitespace(value=html_text, start_index=equals_index + 1)
        extracted_value, next_index = extract_data_audio_value_at(
            value=html_text,
            start_index=value_start_index,
        )

        if extracted_value is not None:
            values.append(extracted_value)

        search_start_index = max(next_index, marker_index + len(marker))

    return tuple(values)


def extract_data_audio_value_at(*, value: str, start_index: int) -> tuple[str | None, int]:
    if start_index >= len(value):
        return None, start_index + 1

    if value.startswith("&quot;", start_index):
        return extract_entity_quoted_data_audio_value(
            value=value,
            start_index=start_index,
            entity="&quot;",
        )

    if value.startswith("&#34;", start_index):
        return extract_entity_quoted_data_audio_value(
            value=value,
            start_index=start_index,
            entity="&#34;",
        )

    quote = value[start_index]

    if quote in {"'", '"'}:
        end_index = find_unescaped_quote_index(
            value=value,
            quote=quote,
            start_index=start_index + 1,
        )

        if end_index is None:
            return None, start_index + 1

        return value[start_index + 1 : end_index], end_index + 1

    json_start_index = find_json_value_start_index(value=value, start_index=start_index)

    if json_start_index is None:
        return None, start_index + 1

    extracted_json = extract_balanced_json_text(value=value, start_index=json_start_index)

    if extracted_json is None:
        return None, json_start_index + 1

    return extracted_json, json_start_index + len(extracted_json)


def extract_entity_quoted_data_audio_value(
    *,
    value: str,
    start_index: int,
    entity: str,
) -> tuple[str | None, int]:
    unescaped_window = repeatedly_unescape_html(value=value[start_index : start_index + 100_000])
    json_start_index = find_json_value_start_index(value=unescaped_window, start_index=0)

    if json_start_index is None:
        return None, start_index + len(entity)

    extracted_json = extract_balanced_json_text(value=unescaped_window, start_index=json_start_index)

    if extracted_json is None:
        return None, start_index + len(entity)

    return extracted_json, start_index + len(entity) + len(extracted_json)


def find_json_value_start_index(*, value: str, start_index: int) -> int | None:
    candidates = tuple(
        index
        for index in (
            value.find("[", start_index),
            value.find("{", start_index),
        )
        if index >= 0
    )

    if not candidates:
        return None

    return min(candidates)


def extract_balanced_json_text(*, value: str, start_index: int) -> str | None:
    opening_character = value[start_index]
    closing_character = "]" if opening_character == "[" else "}"
    depth = 0
    is_inside_string = False
    is_escaped = False

    for index in range(start_index, len(value)):
        character = value[index]

        if is_inside_string:
            if is_escaped:
                is_escaped = False
                continue

            if character == "\\":
                is_escaped = True
                continue

            if character == '"':
                is_inside_string = False

            continue

        if character == '"':
            is_inside_string = True
            continue

        if character == opening_character:
            depth += 1
            continue

        if character != closing_character:
            continue

        depth -= 1

        if depth == 0:
            return value[start_index : index + 1]

    return None


def find_unescaped_quote_index(*, value: str, quote: str, start_index: int) -> int | None:
    is_escaped = False

    for index in range(start_index, len(value)):
        character = value[index]

        if is_escaped:
            is_escaped = False
            continue

        if character == "\\":
            is_escaped = True
            continue

        if character == quote:
            return index

    return None


def skip_whitespace(*, value: str, start_index: int) -> int:
    current_index = start_index

    while current_index < len(value) and value[current_index].isspace():
        current_index += 1

    return current_index


def parse_audio_data_json(*, value: str) -> object | None:
    normalized_value = repeatedly_unescape_html(value=value).strip()

    if len(normalized_value) >= 2 and normalized_value[0] == normalized_value[-1] and normalized_value[0] in {"'", '"'}:
        normalized_value = normalized_value[1:-1].strip()

    json_start_index = find_json_value_start_index(value=normalized_value, start_index=0)

    if json_start_index is not None:
        balanced_json_text = extract_balanced_json_text(
            value=normalized_value,
            start_index=json_start_index,
        )

        if balanced_json_text is not None:
            normalized_value = balanced_json_text

    try:
        return json.loads(normalized_value)
    except json.JSONDecodeError:
        return None


def repeatedly_unescape_html(*, value: str) -> str:
    current_value = value

    for _ in range(5):
        next_value = html_tools.unescape(current_value)

        if next_value == current_value:
            return next_value

        current_value = next_value

    return current_value


def build_track_diagnostic_source(
    *,
    source: str,
    audio_id: VkAudioId,
    tracks: Sequence[VkAudioTrack],
) -> str:
    matched_tracks = tuple(track for track in tracks if track.matches(audio_id))
    tracks_with_full_hash = tuple(track for track in matched_tracks if build_full_id_candidates(track=track))
    tracks_with_direct_url = tuple(track for track in matched_tracks if track.direct_url is not None)
    candidate_ids_count = len(collect_full_id_candidates(audio_id=audio_id, tracks=tracks))

    return (
        f"{source} tracks={len(tracks)} "
        f"matched={len(matched_tracks)} "
        f"matched_hashes={len(tracks_with_full_hash)} "
        f"matched_direct_urls={len(tracks_with_direct_url)} "
        f"candidate_ids={candidate_ids_count}"
    )


def parse_vk_audio_track(*, value: object) -> VkAudioTrack | None:
    if isinstance(value, Mapping):
        return parse_vk_audio_track_from_mapping(value=value)

    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return parse_vk_audio_track_from_sequence(value=value)

    return None


def parse_vk_audio_track_from_mapping(*, value: Mapping[object, object]) -> VkAudioTrack | None:
    owner_id = normalize_int_text(value=get_mapping_value(value, key="owner_id"))
    audio_id = normalize_int_text(value=get_mapping_value(value, key="id"))

    if owner_id is None or audio_id is None:
        return None

    user_id = normalize_optional_int(value=get_mapping_value(value, key="vk_id"))
    direct_url = normalize_optional_text(value=get_mapping_value(value, key="url"))
    direct_url = decode_vk_audio_api_unavailable_url_if_possible(
        url=direct_url,
        user_id=user_id,
    )

    action_hash = normalize_optional_text(value=get_mapping_value(value, key="actionHash"))
    url_hash = normalize_optional_text(value=get_mapping_value(value, key="urlHash"))

    return VkAudioTrack(
        owner_id=owner_id,
        audio_id=audio_id,
        title=normalize_optional_text(value=get_mapping_value(value, key="title")),
        artist=normalize_optional_text(value=get_mapping_value(value, key="artist")),
        duration_seconds=normalize_optional_int(value=get_mapping_value(value, key="duration")),
        direct_url=direct_url,
        action_hash=action_hash,
        url_hash=url_hash,
        user_id=user_id,
    )


def parse_vk_audio_track_from_sequence(*, value: Sequence[object]) -> VkAudioTrack | None:
    if len(value) < 6:
        return None

    audio_id = normalize_int_text(value=value[0])
    owner_id = normalize_int_text(value=value[1])

    if owner_id is None or audio_id is None:
        return None

    user_id = extract_track_user_id(value=value)
    direct_url = normalize_optional_text(value=value[2])
    direct_url = decode_vk_audio_api_unavailable_url_if_possible(
        url=direct_url,
        user_id=user_id,
    )
    action_hash, url_hash = extract_action_and_url_hash(value=value)
    source_owner_id, source_audio_id = extract_source_audio_id(value=value)

    return VkAudioTrack(
        owner_id=owner_id,
        audio_id=audio_id,
        direct_url=direct_url,
        title=strip_html_text(value=normalize_optional_text(value=value[3])),
        artist=strip_html_text(value=normalize_optional_text(value=value[4])),
        duration_seconds=normalize_optional_int(value=value[5]),
        action_hash=action_hash,
        url_hash=url_hash,
        playback_hash=normalize_optional_text_at(value=value, index=20),
        access_key=normalize_optional_text_at(value=value, index=24),
        source_owner_id=source_owner_id,
        source_audio_id=source_audio_id,
        user_id=user_id,
    )


def extract_track_user_id(*, value: Sequence[object]) -> int | None:
    if len(value) <= 15:
        return None

    metadata = value[15]

    if not isinstance(metadata, Mapping):
        return None

    return normalize_optional_int(value=get_mapping_value(metadata, key="vk_id"))


def extract_action_and_url_hash(*, value: Sequence[object]) -> tuple[str | None, str | None]:
    if len(value) <= 13:
        return None, None

    raw_hashes = normalize_optional_text(value=value[13])

    if raw_hashes is None:
        return None, None

    hash_parts = raw_hashes.split("/")

    if len(hash_parts) < MIN_AUDIO_HASH_PARTS_COUNT:
        return None, None

    action_hash = hash_parts[2].strip()
    url_hash = hash_parts[5].strip()

    if not action_hash or not url_hash:
        return None, None

    return action_hash, url_hash


def extract_source_audio_id(*, value: Sequence[object]) -> tuple[str | None, str | None]:
    source_id = normalize_optional_text_at(value=value, index=26)

    if source_id is None:
        return None, None

    source_parts = source_id.split("_", maxsplit=1)

    if len(source_parts) != 2:
        return None, None

    source_owner_id = normalize_int_text(value=source_parts[0])
    source_audio_id = normalize_int_text(value=source_parts[1])

    if source_owner_id is None or source_audio_id is None:
        return None, None

    return source_owner_id, source_audio_id


def normalize_optional_text_at(*, value: Sequence[object], index: int) -> str | None:
    if len(value) <= index:
        return None

    return normalize_optional_text(value=value[index])


def get_mapping_value(value: Mapping[object, object], *, key: str) -> object | None:
    return value.get(key)


def normalize_int_text(*, value: object | None) -> str | None:
    if isinstance(value, int):
        return str(value)

    if not isinstance(value, str):
        return None

    normalized_value = value.strip()

    if normalized_value.removeprefix("-").isdigit():
        return normalized_value

    return None


def normalize_optional_int(*, value: object | None) -> int | None:
    if isinstance(value, int):
        return value

    if not isinstance(value, str):
        return None

    normalized_value = value.strip()

    if normalized_value.isdigit():
        return int(normalized_value)

    return None


def normalize_optional_text(*, value: object | None) -> str | None:
    if not isinstance(value, str):
        return None

    normalized_value = value.strip()

    if not normalized_value:
        return None

    return html_tools.unescape(normalized_value)


def strip_html_text(*, value: str | None) -> str | None:
    if value is None:
        return None

    return re.sub(r"<[^>]+>", "", value).strip() or None


def decode_vk_audio_api_unavailable_url_if_possible(
    *,
    url: str | None,
    user_id: int | None,
) -> str | None:
    if url is None:
        return None

    if "audio_api_unavailable" not in url.casefold():
        return url

    if user_id is None:
        return url

    decoded_url = decode_vk_audio_api_unavailable_url(
        url=url,
        user_id=user_id,
    )

    if decoded_url is None:
        return url

    return convert_m3u8_audio_url_to_mp3_if_possible(url=decoded_url)


def decode_vk_audio_api_unavailable_url(*, url: str, user_id: int) -> str | None:
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query, keep_blank_values=True)
    encoded_url_values = query.get("extra")

    if not encoded_url_values:
        return None

    encoded_url = encoded_url_values[0]
    encoded_operations = parsed_url.fragment

    decoded_url = decode_vk_audio_custom_base64(value=encoded_url)

    if decoded_url is None:
        return None

    decoded_operations = decode_vk_audio_custom_base64(value=encoded_operations)

    if decoded_operations is None:
        return None

    return apply_vk_audio_decode_operations(
        value=decoded_url,
        operations=decoded_operations,
        user_id=user_id,
    )


def decode_vk_audio_custom_base64(*, value: str) -> str | None:
    if not value:
        return ""

    translation_table = str.maketrans(
        VK_AUDIO_OBFUSCATION_ALPHABET,
        STANDARD_BASE64_ALPHABET,
    )
    translated_value = value.translate(translation_table)
    padding = "=" * (-len(translated_value) % 4)

    try:
        decoded_bytes = base64.b64decode(
            translated_value + padding,
            validate=False,
        )
    except ValueError:
        return None

    return decoded_bytes.decode("latin-1")


def apply_vk_audio_decode_operations(
    *,
    value: str,
    operations: str,
    user_id: int,
) -> str | None:
    decoded_value = value
    operation_items = tuple(operation for operation in operations.split(VK_AUDIO_OPERATION_SEPARATOR) if operation)

    for operation in reversed(operation_items):
        decoded_value = apply_vk_audio_decode_operation(
            value=decoded_value,
            operation=operation,
            user_id=user_id,
        )

        if decoded_value is None:
            return None

    if not decoded_value.startswith(("http://", "https://")):
        return None

    return decoded_value


def apply_vk_audio_decode_operation(
    *,
    value: str,
    operation: str,
    user_id: int,
) -> str | None:
    arguments = operation.split(VK_AUDIO_OPERATION_ARGUMENT_SEPARATOR)
    operation_name = arguments[0]

    if operation_name == "v":
        return value[::-1]

    if operation_name == "r":
        operation_argument = parse_vk_audio_operation_int_argument(arguments=arguments)

        if operation_argument is None:
            return None

        return rotate_vk_audio_url(value=value, rotation=operation_argument)

    if operation_name == "s":
        operation_argument = parse_vk_audio_operation_int_argument(arguments=arguments)

        if operation_argument is None:
            return None

        return shuffle_vk_audio_url(value=value, seed=operation_argument)

    if operation_name == "i":
        operation_argument = parse_vk_audio_operation_int_argument(arguments=arguments)

        if operation_argument is None:
            return None

        return shuffle_vk_audio_url(value=value, seed=operation_argument ^ user_id)

    if operation_name == "x":
        if len(arguments) < 2 or not arguments[1]:
            return None

        return xor_vk_audio_url(value=value, key=arguments[1])

    return None


def parse_vk_audio_operation_int_argument(*, arguments: Sequence[str]) -> int | None:
    if len(arguments) < 2:
        return None

    try:
        return int(arguments[1])
    except ValueError:
        return None


def rotate_vk_audio_url(*, value: str, rotation: int) -> str:
    characters = list(value)
    alphabet = VK_AUDIO_OBFUSCATION_ALPHABET * 2

    for index, character in enumerate(characters):
        alphabet_index = alphabet.find(character)

        if alphabet_index >= 0:
            characters[index] = alphabet[alphabet_index - rotation]

    return "".join(characters)


def shuffle_vk_audio_url(*, value: str, seed: int) -> str:
    value_length = len(value)

    if value_length == 0:
        return value

    characters = list(value)
    indexes = build_vk_audio_shuffle_indexes(
        value_length=value_length,
        seed=seed,
    )

    for offset in range(1, value_length):
        swap_index = indexes[value_length - 1 - offset]
        characters[swap_index], characters[offset] = characters[offset], characters[swap_index]

    return "".join(characters)


def build_vk_audio_shuffle_indexes(*, value_length: int, seed: int) -> tuple[int, ...]:
    indexes: dict[int, int] = {}
    position = value_length
    current_seed = abs(seed)

    while position:
        position -= 1
        current_seed = (value_length * (position + 1) ^ current_seed + position) % value_length
        indexes[position] = current_seed

    return tuple(indexes[index] for index in sorted(indexes))


def xor_vk_audio_url(*, value: str, key: str) -> str:
    key_code = ord(key[0])

    return "".join(chr(ord(character) ^ key_code) for character in value)


def find_direct_audio_url(*, value: object) -> str | None:
    for candidate in iter_audio_url_candidates(value=value):
        normalized_candidate = normalize_direct_audio_url_candidate(value=candidate)

        if normalized_candidate is not None:
            return normalized_candidate

    return None


def iter_audio_url_candidates(*, value: object) -> tuple[str, ...]:
    candidates: list[str] = []

    for string_value in iter_string_values(value=value):
        candidates.append(string_value)
        candidates.extend(match.group(0) for match in EMBEDDED_URL_RE.finditer(string_value))

    return tuple(candidates)


def normalize_direct_audio_url_candidate(*, value: str) -> str | None:
    candidate = html_tools.unescape(value).replace("\\/", "/").strip()

    if candidate.startswith("//"):
        candidate = f"https:{candidate}"

    if not candidate:
        return None

    normalized_candidate = candidate.casefold()

    if "audio_api_unavailable" in normalized_candidate:
        return None

    if normalized_candidate.startswith("android-app://"):
        return None

    parsed_url = urlparse(candidate)

    if parsed_url.scheme not in {"http", "https"}:
        return None

    if not parsed_url.netloc:
        return None

    host = parsed_url.netloc.casefold()

    if host in REJECTED_MEDIA_HOSTS:
        return None

    normalized_path = parsed_url.path.casefold()
    suffix = Path(normalized_path).suffix

    if suffix in SUPPORTED_AUDIO_MEDIA_EXTENSIONS:
        return candidate

    if is_probable_vk_audio_cdn_url(host=host, path=normalized_path):
        return candidate

    return None


def is_probable_vk_audio_cdn_url(*, host: str, path: str) -> bool:
    if "userapi.com" not in host and "vkuseraudio" not in host and "vk-cdn" not in host:
        return False

    return "/audio/" in path or "audio" in path


def convert_m3u8_audio_url_to_mp3_if_possible(*, url: str) -> str:
    return M3U8_TO_MP3_RE.sub(r"\1/\2.mp3", url)


def has_bad_hash_response(*, response_dump_parts: Iterable[tuple[str, str]]) -> bool:
    return any("bad_hash" in response_text.casefold() for _, response_text in response_dump_parts)


def has_audio_api_unavailable_response(*, response_dump_parts: Iterable[tuple[str, str]]) -> bool:
    return any("audio_api_unavailable" in response_text.casefold() for _, response_text in response_dump_parts)


def build_dump_response_marker_diagnostics_text(
    *,
    response_dump_parts: Sequence[tuple[str, str]],
) -> str:
    if not response_dump_parts:
        return "responses=0"

    return " | ".join(
        format_response_marker_diagnostics(
            source=source,
            response_text=response_text,
        )
        for source, response_text in response_dump_parts
    )


def format_response_marker_diagnostics(*, source: str, response_text: str) -> str:
    normalized_text = response_text.casefold()

    return (
        f"{source}: length={len(response_text)}, "
        f"data_audio={'data-audio' in normalized_text}, "
        f"audio_item={'audio_item' in normalized_text}, "
        f"secondary_attachment={'secondaryattachment' in normalized_text}, "
        f"bad_hash={'bad_hash' in normalized_text}, "
        f"audio_api_unavailable={'audio_api_unavailable' in normalized_text}, "
        f"payload={'payload' in normalized_text}, "
        f"login={'login' in normalized_text or 'remixsid' in normalized_text}"
    )


def build_response_diagnostics(
    *,
    source: str,
    value: object,
    raw_text: str,
) -> VkResponseDiagnostics:
    string_values = iter_string_values(value=value)
    embedded_url_candidates = tuple(
        match.group(0) for string_value in string_values for match in EMBEDDED_URL_RE.finditer(string_value)
    )
    normalized_raw_text = raw_text.casefold()

    return VkResponseDiagnostics(
        source=source,
        length=len(raw_text),
        strings_count=len(string_values),
        embedded_url_candidates_count=len(embedded_url_candidates),
        has_bad_hash="bad_hash" in normalized_raw_text,
        has_audio_api_unavailable="audio_api_unavailable" in normalized_raw_text,
        has_payload_marker="payload" in normalized_raw_text,
        has_login_marker=("login" in normalized_raw_text or "remixsid" in normalized_raw_text),
        safe_preview=build_safe_response_preview(text=raw_text),
    )


def build_safe_response_preview(*, text: str) -> str:
    compact_text = " ".join(text.strip().split())
    redacted_text = EMBEDDED_URL_RE.sub("<redacted-url>", compact_text)

    if len(redacted_text) <= RESPONSE_PREVIEW_LENGTH:
        return redacted_text

    return f"{redacted_text[:RESPONSE_PREVIEW_LENGTH]}..."


def find_string_containing(*, value: object, needle: str) -> str | None:
    normalized_needle = needle.casefold()

    for candidate in iter_string_values(value=value):
        if normalized_needle in candidate.casefold():
            return candidate

    return None


def iter_string_values(*, value: object) -> tuple[str, ...]:
    values: list[str] = []
    stack: list[object] = [value]

    while stack:
        current_value = stack.pop()

        if isinstance(current_value, str):
            values.append(current_value)
            continue

        if isinstance(current_value, Mapping):
            stack.extend(current_value.values())
            continue

        if isinstance(current_value, Sequence) and not isinstance(current_value, bytes):
            stack.extend(current_value)

    return tuple(values)


def dump_vk_responses_if_requested(
    *,
    dump_response_file: Path | None,
    response_dump_parts: Sequence[tuple[str, str]],
) -> None:
    if dump_response_file is None:
        return

    dump_vk_responses(
        dump_response_file=dump_response_file,
        response_dump_parts=response_dump_parts,
    )


def dump_vk_responses(
    *,
    dump_response_file: Path,
    response_dump_parts: Sequence[tuple[str, str]],
) -> None:
    dump_response_file.parent.mkdir(parents=True, exist_ok=True)
    sections: list[str] = []

    for title, response_text in response_dump_parts:
        sections.extend(
            [
                f"===== {title} =====",
                response_text,
                "",
            ]
        )

    try:
        dump_response_file.write_text("\n".join(sections), encoding="utf-8", newline="\n")
    except OSError as error:
        raise VkAudioProbeError(f"не удалось записать debug response: {error}") from error


def download_direct_audio(
    *,
    media: VkAudioDirectMedia,
    download_dir: Path,
    timeout_seconds: float,
    output_format: str = DEFAULT_AUDIO_OUTPUT_FORMAT,
    ffmpeg_path: Path | None = None,
) -> Path:
    normalized_output_format = normalize_output_format(output_format=output_format)
    download_dir.mkdir(parents=True, exist_ok=True)
    output_path = build_unique_output_path(
        download_dir=download_dir,
        file_stem=build_output_file_stem(media=media),
        extension=resolve_output_extension(
            url=media.direct_url,
            output_format=normalized_output_format,
        ),
    )

    if is_hls_playlist_url(url=media.direct_url):
        return download_hls_audio_with_ffmpeg(
            media=media,
            output_path=output_path,
            output_format=normalized_output_format,
            ffmpeg_path=ffmpeg_path,
        )

    return download_direct_audio_file(
        media=media,
        output_path=output_path,
        timeout_seconds=timeout_seconds,
    )


def normalize_output_format(*, output_format: str) -> str:
    normalized_output_format = output_format.strip().casefold()

    if normalized_output_format not in VK_AUDIO_OUTPUT_FORMATS:
        supported_formats = ", ".join(VK_AUDIO_OUTPUT_FORMATS)
        raise VkAudioProbeError(
            f"неподдерживаемый формат VK Audio: {output_format}. Поддерживаются: {supported_formats}"
        )

    return normalized_output_format


def download_hls_audio_with_ffmpeg(
    *,
    media: VkAudioDirectMedia,
    output_path: Path,
    output_format: str,
    ffmpeg_path: Path | None,
) -> Path:
    ffmpeg_executable = resolve_ffmpeg_executable(ffmpeg_path=ffmpeg_path)
    command = build_ffmpeg_hls_download_command(
        ffmpeg_executable=ffmpeg_executable,
        media_url=media.direct_url,
        output_path=output_path,
        output_format=output_format,
    )

    try:
        completed_process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=FFMPEG_DOWNLOAD_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise VkAudioProbeError("FFmpeg не успел скачать VK Audio HLS за отведённое время") from error
    except OSError as error:
        raise VkAudioProbeError(f"не удалось запустить FFmpeg: {error}") from error

    if completed_process.returncode != 0:
        error_text = (completed_process.stderr or completed_process.stdout).strip()
        if not error_text:
            error_text = f"FFmpeg завершился с кодом {completed_process.returncode}"

        raise VkAudioProbeError(f"FFmpeg не смог скачать VK Audio HLS: {error_text}")

    if not output_path.is_file():
        raise VkAudioProbeError("FFmpeg завершился успешно, но итоговый аудиофайл не найден")

    return output_path


def resolve_ffmpeg_executable(*, ffmpeg_path: Path | None) -> Path:
    if ffmpeg_path is not None:
        resolved_path = ffmpeg_path.expanduser().resolve()

        if not resolved_path.is_file():
            raise VkAudioProbeError(f"FFmpeg не найден по указанному пути: {resolved_path}")

        return resolved_path

    system_ffmpeg = shutil.which(FFMPEG_EXECUTABLE_NAME)

    if system_ffmpeg is not None:
        return Path(system_ffmpeg).resolve()

    app_managed_ffmpeg = find_app_managed_ffmpeg_executable()

    if app_managed_ffmpeg is not None:
        return app_managed_ffmpeg

    raise VkAudioProbeError(
        "для скачивания VK Audio HLS нужен FFmpeg. Установите FFmpeg через YaLoader или передайте --ffmpeg-path."
    )


def find_app_managed_ffmpeg_executable() -> Path | None:
    appdata_dir = os.getenv("APPDATA")

    if appdata_dir is None:
        return None

    candidate = Path(appdata_dir) / "yaloader" / "tools" / "ffmpeg" / "bin" / FFMPEG_WINDOWS_EXECUTABLE_NAME

    if not candidate.is_file():
        return None

    return candidate.resolve()


def build_ffmpeg_hls_download_command(
    *,
    ffmpeg_executable: Path,
    media_url: str,
    output_path: Path,
    output_format: str,
) -> tuple[str, ...]:
    return (
        str(ffmpeg_executable),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-headers",
        build_ffmpeg_headers_argument(),
        "-i",
        media_url,
        "-vn",
        *build_ffmpeg_audio_codec_args(output_format=output_format),
        str(output_path),
    )


def build_ffmpeg_headers_argument() -> str:
    return "".join(
        f"{header_name}: {header_value}\r\n"
        for header_name, header_value in VK_MOBILE_AUDIO_REQUEST_HEADERS.items()
        if header_name.casefold() in {"user-agent", "referer", "origin"}
    )


def build_ffmpeg_audio_codec_args(*, output_format: str) -> tuple[str, ...]:
    if output_format == "mp3":
        return ("-c:a", "libmp3lame", "-q:a", "0")

    if output_format == "m4a":
        return ("-c:a", "aac", "-b:a", "192k")

    raise VkAudioProbeError(f"неподдерживаемый формат FFmpeg для VK Audio: {output_format}")


def download_direct_audio_file(
    *,
    media: VkAudioDirectMedia,
    output_path: Path,
    timeout_seconds: float,
) -> Path:
    try:
        with httpx.stream(
            "GET",
            media.direct_url,
            follow_redirects=True,
            timeout=timeout_seconds,
            headers=VK_MOBILE_AUDIO_REQUEST_HEADERS,
        ) as response:
            response.raise_for_status()

            with output_path.open("wb") as output_file:
                for chunk in response.iter_bytes(chunk_size=DOWNLOAD_CHUNK_SIZE_BYTES):
                    if chunk:
                        output_file.write(chunk)
    except httpx.HTTPStatusError as error:
        raise VkAudioProbeError(f"прямая media-ссылка вернула HTTP {error.response.status_code}") from error
    except httpx.HTTPError as error:
        raise VkAudioProbeError(f"не удалось скачать прямую media-ссылку: {error}") from error
    except OSError as error:
        raise VkAudioProbeError(f"не удалось записать файл: {error}") from error

    return output_path


def is_hls_playlist_url(*, url: str) -> bool:
    return Path(urlparse(url).path).suffix.casefold() == ".m3u8"


def resolve_output_extension(*, url: str, output_format: str) -> str:
    if is_hls_playlist_url(url=url):
        return f".{output_format}"

    return resolve_audio_extension(url=url)


def build_output_file_stem(*, media: VkAudioDirectMedia) -> str:
    title = format_track_title(artist=media.artist, title=media.title)

    if title is None:
        return media.audio_id.safe_file_stem

    return sanitize_file_stem(value=title)


def format_track_title(*, artist: str | None, title: str | None) -> str | None:
    if artist is not None and title is not None:
        return f"{artist} - {title}"

    return title or artist


def sanitize_file_stem(*, value: str) -> str:
    sanitized_value = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", value).strip(" ._")

    if sanitized_value:
        return sanitized_value

    return "vk_audio"


def resolve_audio_extension(*, url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()

    if suffix in SUPPORTED_AUDIO_MEDIA_EXTENSIONS:
        return suffix

    return FALLBACK_AUDIO_EXTENSION


def build_unique_output_path(
    *,
    download_dir: Path,
    file_stem: str,
    extension: str,
) -> Path:
    candidate = download_dir / f"{file_stem}{extension}"

    if not candidate.exists():
        return candidate

    duplicate_index = 1

    while True:
        candidate = download_dir / f"{file_stem} ({duplicate_index}){extension}"

        if not candidate.exists():
            return candidate

        duplicate_index += 1


def redact_url_query(*, url: str) -> str:
    parsed_url = urlparse(url)

    if not parsed_url.query:
        return url

    return parsed_url._replace(query="<redacted>").geturl()


if __name__ == "__main__":
    raise SystemExit(main())
