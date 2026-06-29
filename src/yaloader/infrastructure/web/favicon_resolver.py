from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import quote, urlparse

import httpx
from loguru import logger

FAVICON_HTTP_TIMEOUT_SECONDS: Final = 6.0
MAX_FAVICON_SIZE_BYTES: Final = 1 * 1024 * 1024
FAVICON_CACHE_KEY_LENGTH: Final = 24
FAVICON_USER_AGENT: Final = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) YaLoader"

FAVICON_FILE_SUFFIXES: Final[tuple[str, ...]] = (
    ".png",
    ".ico",
    ".jpg",
    ".jpeg",
    ".svg",
    ".webp",
)

SUPPORTED_FAVICON_CONTENT_TYPES: Final[tuple[str, ...]] = (
    "image/png",
    "image/x-png",
    "image/jpeg",
    "image/jpg",
    "image/x-icon",
    "image/vnd.microsoft.icon",
    "image/svg+xml",
    "image/webp",
)


@dataclass(frozen=True, slots=True)
class WebFaviconResolver:
    cache_dir: Path
    timeout_seconds: float = FAVICON_HTTP_TIMEOUT_SECONDS
    max_icon_size_bytes: int = MAX_FAVICON_SIZE_BYTES

    def resolve_icon_path(self, *, url: str) -> Path | None:
        host = extract_favicon_host(url=url)

        if host is None:
            return None

        cached_icon_path = find_cached_favicon_path(cache_dir=self.cache_dir, host=host)

        if cached_icon_path is not None:
            return cached_icon_path

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=self.timeout_seconds,
                headers={"User-Agent": FAVICON_USER_AGENT},
            ) as client:
                for candidate_url in build_favicon_url_candidates(url=url):
                    icon_path = self._download_candidate(
                        client=client,
                        host=host,
                        candidate_url=candidate_url,
                    )

                    if icon_path is not None:
                        return icon_path
        except httpx.HTTPError as error:
            logger.debug("Favicon resolver failed. url={} error={}", url, error)

        return None

    def _download_candidate(
        self,
        *,
        client: httpx.Client,
        host: str,
        candidate_url: str,
    ) -> Path | None:
        try:
            response = client.get(candidate_url)
        except httpx.HTTPError as error:
            logger.debug(
                "Favicon candidate request failed. url={} error={}",
                candidate_url,
                error,
            )
            return None

        if response.status_code != httpx.codes.OK:
            return None

        content_length = parse_content_length(value=response.headers.get("content-length"))

        if content_length is not None and content_length > self.max_icon_size_bytes:
            return None

        if not is_supported_favicon_response(response=response, candidate_url=candidate_url):
            return None

        content = response.content

        if not content or len(content) > self.max_icon_size_bytes:
            return None

        content_type = get_response_content_type(response=response)
        suffix = infer_favicon_file_suffix(
            candidate_url=candidate_url,
            content_type=content_type,
        )
        icon_path = self.cache_dir / f"{build_favicon_cache_key(host=host)}{suffix}"
        temporary_icon_path = icon_path.with_name(f"{icon_path.name}.tmp")

        try:
            temporary_icon_path.write_bytes(content)
            temporary_icon_path.replace(icon_path)
        except OSError as error:
            logger.debug(
                "Failed to cache favicon. path={} error={}",
                icon_path,
                error,
            )
            return None
        finally:
            remove_file_if_exists(file_path=temporary_icon_path)

        return icon_path


def extract_favicon_host(*, url: str) -> str | None:
    parsed_url = urlparse(url.strip())

    return normalize_favicon_host(host=parsed_url.hostname)


def normalize_favicon_host(*, host: str | None) -> str | None:
    if host is None:
        return None

    normalized_host = host.strip().rstrip(".").casefold()

    if not normalized_host:
        return None

    return normalized_host


def build_favicon_url_candidates(*, url: str) -> tuple[str, ...]:
    host = extract_favicon_host(url=url)

    if host is None:
        return ()

    candidates: list[str] = []

    for host_variant in build_favicon_host_variants(host=host):
        candidates.extend(
            (
                f"https://{host_variant}/favicon.ico",
                f"https://{host_variant}/favicon.png",
                f"https://{host_variant}/apple-touch-icon.png",
            )
        )

    fallback_domain = host.removeprefix("www.")
    encoded_host = quote(host, safe="")
    encoded_fallback_domain = quote(fallback_domain, safe="")

    candidates.extend(
        (
            f"https://icons.duckduckgo.com/ip3/{encoded_host}.ico",
            f"https://icons.duckduckgo.com/ip3/{encoded_fallback_domain}.ico",
            f"https://www.google.com/s2/favicons?domain={encoded_host}&sz=64",
            f"https://www.google.com/s2/favicons?domain={encoded_fallback_domain}&sz=64",
        )
    )

    return tuple(dict.fromkeys(candidates))


def build_favicon_host_variants(*, host: str) -> tuple[str, ...]:
    variants = [host]

    if host.startswith("www."):
        variants.append(host.removeprefix("www."))
    else:
        variants.append(f"www.{host}")

    return tuple(dict.fromkeys(variants))


def build_favicon_cache_key(*, host: str) -> str:
    normalized_host = normalize_favicon_host(host=host)

    if normalized_host is None:
        return "unknown"

    return hashlib.sha256(normalized_host.encode("utf-8")).hexdigest()[:FAVICON_CACHE_KEY_LENGTH]


def find_cached_favicon_path(*, cache_dir: Path, host: str) -> Path | None:
    cache_key = build_favicon_cache_key(host=host)

    for suffix in FAVICON_FILE_SUFFIXES:
        candidate = cache_dir / f"{cache_key}{suffix}"

        if candidate.is_file():
            return candidate

    return None


def parse_content_length(*, value: str | None) -> int | None:
    if value is None:
        return None

    try:
        content_length = int(value)
    except ValueError:
        return None

    if content_length <= 0:
        return None

    return content_length


def get_response_content_type(*, response: httpx.Response) -> str:
    raw_content_type = response.headers.get("content-type")

    if raw_content_type is None:
        return ""

    return str(raw_content_type).partition(";")[0].strip().casefold()


def is_supported_favicon_response(
    *,
    response: httpx.Response,
    candidate_url: str,
) -> bool:
    content_type = get_response_content_type(response=response)

    if content_type in SUPPORTED_FAVICON_CONTENT_TYPES:
        return True

    candidate_suffix = Path(urlparse(candidate_url).path).suffix.casefold()

    return candidate_suffix in FAVICON_FILE_SUFFIXES


def infer_favicon_file_suffix(*, candidate_url: str, content_type: str) -> str:
    normalized_content_type = content_type.strip().casefold()

    if normalized_content_type in {"image/png", "image/x-png"}:
        return ".png"

    if normalized_content_type in {"image/jpeg", "image/jpg"}:
        return ".jpg"

    if normalized_content_type in {"image/x-icon", "image/vnd.microsoft.icon"}:
        return ".ico"

    if normalized_content_type == "image/svg+xml":
        return ".svg"

    if normalized_content_type == "image/webp":
        return ".webp"

    candidate_suffix = Path(urlparse(candidate_url).path).suffix.casefold()

    if candidate_suffix in FAVICON_FILE_SUFFIXES:
        return candidate_suffix

    return ".png"


def remove_file_if_exists(*, file_path: Path) -> None:
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        return
