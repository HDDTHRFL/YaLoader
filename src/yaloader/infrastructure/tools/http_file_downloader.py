from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

ArchiveDownloadProgressCallback = Callable[[int, int | None], None]

HTTP_DOWNLOAD_TIMEOUT_SECONDS = 180.0
HTTP_DOWNLOAD_CHUNK_SIZE_BYTES = 1024 * 512


class FileDownloadError(RuntimeError):
    pass


class FileDownloader(Protocol):
    def download_file(
        self,
        *,
        url: str,
        destination_file: Path,
        progress_callback: ArchiveDownloadProgressCallback | None = None,
    ) -> None: ...

    def download_text(self, *, url: str) -> str: ...


@dataclass(frozen=True, slots=True)
class HttpFileDownloader:
    timeout_seconds: float = HTTP_DOWNLOAD_TIMEOUT_SECONDS
    chunk_size_bytes: int = HTTP_DOWNLOAD_CHUNK_SIZE_BYTES

    def download_file(
        self,
        *,
        url: str,
        destination_file: Path,
        progress_callback: ArchiveDownloadProgressCallback | None = None,
    ) -> None:
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        downloaded_bytes = 0

        try:
            with httpx.stream(
                "GET",
                url,
                follow_redirects=True,
                timeout=self.timeout_seconds,
            ) as response:
                response.raise_for_status()
                total_bytes = parse_content_length(value=response.headers.get("content-length"))

                with destination_file.open("wb") as file:
                    for chunk in response.iter_bytes(chunk_size=self.chunk_size_bytes):
                        if not chunk:
                            continue

                        file.write(chunk)
                        downloaded_bytes += len(chunk)

                        if progress_callback is not None:
                            progress_callback(downloaded_bytes, total_bytes)
        except httpx.HTTPError as error:
            raise FileDownloadError(f"download failed: {url}: {error}") from error

    def download_text(self, *, url: str) -> str:
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=self.timeout_seconds,
            ) as client:
                response = client.get(url)
                response.raise_for_status()

                return response.text
        except httpx.HTTPError as error:
            raise FileDownloadError(f"text download failed: {url}: {error}") from error


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
