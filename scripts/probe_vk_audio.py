from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import urlparse

import httpx

VK_AUDIO_RELOAD_URL: Final = "https://vk.com/al_audio.php?act=reload_audio"
VK_AUDIO_URL_RE: Final = re.compile(
    r"^/audio(?P<owner_id>-?\d+)_(?P<audio_id>\d+)(?:_(?P<access_key>[A-Za-z0-9]+))?/?$"
)
EMBEDDED_URL_RE: Final = re.compile(r"(?:https?:)?\\?/\\?/[^\s\"'<>]+")
SUPPORTED_AUDIO_MEDIA_EXTENSIONS: Final = frozenset({".mp3", ".m4a", ".aac", ".ogg", ".opus", ".m3u8"})
REJECTED_MEDIA_HOSTS: Final = frozenset(
    {
        "com.vkontakte.android",
        "vk.com",
        "www.vk.com",
        "m.vk.com",
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
RESPONSE_PREVIEW_LENGTH: Final = 220

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
    def display_value(self) -> str:
        if self.access_key is None:
            return self.value

        return f"{self.owner_id}_{self.audio_id}_<access-key>"

    @property
    def safe_file_stem(self) -> str:
        return f"vk_audio_{self.owner_id}_{self.audio_id}"


@dataclass(frozen=True, slots=True)
class VkAudioDirectMedia:
    audio_id: VkAudioId
    direct_url: str


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
    sys.stdout.write(f"Direct media:  {redact_url_query(url=media.direct_url)}\n")

    if parsed_args.download_dir is None:
        return 0

    try:
        output_path = download_direct_audio(
            media=media,
            download_dir=parsed_args.download_dir.resolve(),
            timeout_seconds=parsed_args.timeout,
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
    cookies = load_netscape_cookies(cookies_file=cookies_file)

    if not cookies:
        raise VkAudioProbeError(f"cookies.txt не содержит cookies для запроса VK Audio: {cookies_file}")

    reload_response_text = request_vk_audio_reload(
        audio_id=audio_id,
        cookies=cookies,
        timeout_seconds=timeout_seconds,
    )
    reload_payload = parse_vk_al_json_payload(text=reload_response_text)
    direct_url = find_direct_audio_url(value=reload_payload)

    page_response_text: str | None = None

    if direct_url is None:
        page_response_text = request_vk_audio_page(
            url=url,
            cookies=cookies,
            timeout_seconds=timeout_seconds,
        )
        direct_url = find_direct_audio_url(value=page_response_text)

    if dump_response_file is not None:
        dump_vk_responses(
            dump_response_file=dump_response_file,
            reload_response_text=reload_response_text,
            page_response_text=page_response_text,
        )

    if direct_url is not None:
        return VkAudioDirectMedia(
            audio_id=audio_id,
            direct_url=direct_url,
        )

    bad_hash_marker = find_string_containing(value=reload_payload, needle="bad_hash")

    if bad_hash_marker is not None:
        raise VkAudioProbeError(
            "VK reload_audio вернул bad_hash. "
            "Это значит, что прямой запрос al_audio.php требует дополнительный актуальный hash, "
            "который нельзя получить только из обычной audio-ссылки. "
            "Текущий web-page fallback тоже не содержит прямой media URL."
        )

    reload_diagnostics = build_response_diagnostics(
        source="reload_audio",
        value=reload_payload,
        raw_text=reload_response_text,
    )
    page_diagnostics = None

    if page_response_text is not None:
        page_diagnostics = build_response_diagnostics(
            source="audio_page",
            value=page_response_text,
            raw_text=page_response_text,
        )

    diagnostic_parts = [reload_diagnostics.format_for_error()]

    if page_diagnostics is not None:
        diagnostic_parts.append(page_diagnostics.format_for_error())

    raise VkAudioProbeError("VK ответил, но прямой media URL не найден. Диагностика: " + " | ".join(diagnostic_parts))


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


def request_vk_audio_reload(
    *,
    audio_id: VkAudioId,
    cookies: Mapping[str, str],
    timeout_seconds: float,
) -> str:
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout_seconds,
            cookies=dict(cookies),
            headers=VK_AUDIO_REQUEST_HEADERS,
        ) as client:
            response = client.post(
                VK_AUDIO_RELOAD_URL,
                data={
                    "al": "1",
                    "ids": audio_id.value,
                },
            )
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as error:
        raise VkAudioProbeError(f"VK reload_audio вернул HTTP {error.response.status_code}") from error
    except httpx.HTTPError as error:
        raise VkAudioProbeError(f"VK reload_audio недоступен или запрос не выполнен: {error}") from error


def request_vk_audio_page(
    *,
    url: str,
    cookies: Mapping[str, str],
    timeout_seconds: float,
) -> str:
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout_seconds,
            cookies=dict(cookies),
            headers=VK_AUDIO_REQUEST_HEADERS,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as error:
        raise VkAudioProbeError(f"VK audio page вернул HTTP {error.response.status_code}") from error
    except httpx.HTTPError as error:
        raise VkAudioProbeError(f"VK audio page недоступна или запрос не выполнен: {error}") from error


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


def find_first_json_start_index(*, text: str) -> int | None:
    candidates = tuple(index for index in (text.find("{"), text.find("[")) if index >= 0)

    if not candidates:
        return None

    return min(candidates)


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
    candidate = html.unescape(value).replace("\\/", "/").strip()

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


def dump_vk_responses(
    *,
    dump_response_file: Path,
    reload_response_text: str,
    page_response_text: str | None,
) -> None:
    dump_response_file.parent.mkdir(parents=True, exist_ok=True)
    sections = [
        "===== reload_audio response =====",
        reload_response_text,
    ]

    if page_response_text is not None:
        sections.extend(
            [
                "",
                "===== audio page response =====",
                page_response_text,
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
) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)
    output_path = build_unique_output_path(
        download_dir=download_dir,
        file_stem=media.audio_id.safe_file_stem,
        extension=resolve_audio_extension(url=media.direct_url),
    )

    try:
        with httpx.stream(
            "GET",
            media.direct_url,
            follow_redirects=True,
            timeout=timeout_seconds,
            headers=VK_AUDIO_REQUEST_HEADERS,
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
