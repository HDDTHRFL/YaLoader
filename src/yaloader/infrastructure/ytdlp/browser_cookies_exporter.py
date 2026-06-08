from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self, cast

from yaloader.application.dto.browser_cookies import (
    BrowserCookiesExportResult,
    BrowserId,
    build_browser_cookies_export_progress,
)
from yaloader.application.ports.browser_cookies_exporter import (
    BrowserCookiesExportProgressCallback,
)
from yaloader.application.services.cookies_file_service import validate_cookies_file

TEMPORARY_COOKIES_FILE_SUFFIX = ".tmp"

EXPORT_START_PERCENT = 0
EXPORT_BROWSER_READ_PERCENT = 20
EXPORT_COOKIE_SAVE_PERCENT = 65
EXPORT_VALIDATION_PERCENT = 85
EXPORT_COMPLETED_PERCENT = 100

YtDlpBrowserCookiesOptions = dict[str, object]


class YtDlpBrowserCookieJar(Protocol):
    def save(
        self,
        filename: str | None = None,
        ignore_discard: bool = False,
        ignore_expires: bool = False,
    ) -> None: ...


class YtDlpBrowserCookiesRuntime(Protocol):
    cookiejar: YtDlpBrowserCookieJar

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...


class YtDlpBrowserCookiesFactory(Protocol):
    def __call__(
        self,
        params: YtDlpBrowserCookiesOptions,
    ) -> YtDlpBrowserCookiesRuntime: ...


@dataclass(frozen=True, slots=True)
class YtDlpBrowserCookiesExporter:
    youtube_dl_factory: YtDlpBrowserCookiesFactory = field(
        default_factory=lambda: load_youtube_dl_browser_cookies_factory()
    )

    def export(
        self,
        *,
        browser_id: BrowserId,
        target_file: Path,
        progress_callback: BrowserCookiesExportProgressCallback | None = None,
    ) -> BrowserCookiesExportResult:
        temporary_file = build_temporary_cookies_file(target_file=target_file)

        try:
            self._emit_progress(
                progress_callback=progress_callback,
                browser_id=browser_id,
                message=f"Готовим экспорт cookies из {browser_id.value}",
                percent=EXPORT_START_PERCENT,
            )

            target_file.parent.mkdir(parents=True, exist_ok=True)
            remove_file_if_exists(file_path=temporary_file)

            self._emit_progress(
                progress_callback=progress_callback,
                browser_id=browser_id,
                message=f"Читаем cookies из {browser_id.value}",
                percent=EXPORT_BROWSER_READ_PERCENT,
            )

            options = build_ytdlp_browser_cookie_options(
                browser_id=browser_id,
                cookie_file=temporary_file,
            )

            self._emit_progress(
                progress_callback=progress_callback,
                browser_id=browser_id,
                message="Сохраняем cookies.txt",
                percent=EXPORT_COOKIE_SAVE_PERCENT,
            )

            with self.youtube_dl_factory(options) as downloader:
                save_ytdlp_browser_cookie_file(
                    downloader=downloader,
                    cookie_file=temporary_file,
                )

            self._emit_progress(
                progress_callback=progress_callback,
                browser_id=browser_id,
                message="Проверяем формат cookies.txt",
                percent=EXPORT_VALIDATION_PERCENT,
            )

            validate_cookies_file(source_file=temporary_file)
            temporary_file.replace(target_file)

            self._emit_progress(
                progress_callback=progress_callback,
                browser_id=browser_id,
                message="cookies.txt создан",
                percent=EXPORT_COMPLETED_PERCENT,
                path=target_file,
            )

            return BrowserCookiesExportResult.exported(
                browser_id=browser_id,
                cookies_file=target_file,
            )
        except Exception as error:
            return BrowserCookiesExportResult.failed(
                browser_id=browser_id,
                message=build_browser_cookies_export_error_message(
                    browser_id=browser_id,
                    error=error,
                ),
            )
        finally:
            remove_file_if_exists(file_path=temporary_file)

    def _emit_progress(
        self,
        *,
        progress_callback: BrowserCookiesExportProgressCallback | None,
        browser_id: BrowserId,
        message: str,
        percent: int | None = None,
        path: Path | None = None,
    ) -> None:
        if progress_callback is None:
            return

        progress_callback(
            build_browser_cookies_export_progress(
                browser_id=browser_id,
                message=message,
                percent=percent,
                path=path,
            )
        )


def build_ytdlp_browser_cookie_options(
    *,
    browser_id: BrowserId,
    cookie_file: Path,
) -> YtDlpBrowserCookiesOptions:
    return {
        "cookiesfrombrowser": (browser_id.value, None, None, None),
        "cookiefile": str(cookie_file),
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "simulate": True,
        "noprogress": True,
    }


def save_ytdlp_browser_cookie_file(
    *,
    downloader: YtDlpBrowserCookiesRuntime,
    cookie_file: Path,
) -> None:
    downloader.cookiejar.save(
        str(cookie_file),
        ignore_discard=True,
        ignore_expires=True,
    )


def build_temporary_cookies_file(*, target_file: Path) -> Path:
    return target_file.with_name(f"{target_file.name}{TEMPORARY_COOKIES_FILE_SUFFIX}")


def remove_file_if_exists(*, file_path: Path) -> None:
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        return


def build_browser_cookies_export_error_message(
    *,
    browser_id: BrowserId,
    error: Exception,
) -> str:
    error_message = str(error).strip()

    if not error_message:
        return f"Не удалось создать cookies.txt из {browser_id.value}"

    return f"Не удалось создать cookies.txt из {browser_id.value}: {error_message}"


def load_youtube_dl_browser_cookies_factory() -> YtDlpBrowserCookiesFactory:
    ytdlp_module = importlib.import_module("yt_dlp")
    return cast(YtDlpBrowserCookiesFactory, ytdlp_module.YoutubeDL)
