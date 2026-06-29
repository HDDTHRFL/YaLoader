from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Final, Protocol, Self, cast

from yaloader.application.dto.browser_cookies import (
    BrowserCookiesExportResult,
    BrowserId,
    build_browser_cookies_export_progress,
)
from yaloader.application.ports.browser_cookies_exporter import (
    BrowserCookiesExportProgressCallback,
)
from yaloader.application.services.cookies_file_service import (
    compact_cookies_file_in_place,
    validate_cookies_file,
)
from yaloader.infrastructure.ytdlp.runtime_manager import (
    YtDlpRuntimeManager,
    load_bundled_ytdlp_module,
)

TEMPORARY_COOKIES_FILE_SUFFIX = ".tmp"

CHROMIUM_BROWSER_ID = "chrome"
YANDEX_BROWSER_PROFILE_RELATIVE_PATH = Path("Yandex") / "YandexBrowser" / "User Data" / "Default"

CHROME_COOKIE_DATABASE_COPY_ERROR_MARKER: Final = "Could not copy Chrome cookie database"

BROWSER_DISPLAY_NAMES: Final[Mapping[BrowserId, str]] = {
    BrowserId.FIREFOX: "Firefox",
    BrowserId.OPERA: "Opera",
    BrowserId.CHROME: "Chrome",
    BrowserId.YANDEX: "Яндекс Браузера",
}

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

            compact_cookies_file_in_place(file_path=temporary_file)

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
        "cookiesfrombrowser": build_ytdlp_browser_cookie_source(browser_id=browser_id),
        "cookiefile": str(cookie_file),
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "simulate": True,
        "noprogress": True,
    }


def build_ytdlp_browser_cookie_source(
    *,
    browser_id: BrowserId,
) -> tuple[str, str | None, None, None]:
    if browser_id is BrowserId.YANDEX:
        return (
            CHROMIUM_BROWSER_ID,
            str(get_default_yandex_browser_profile_dir()),
            None,
            None,
        )

    return (browser_id.value, None, None, None)


def get_default_yandex_browser_profile_dir() -> Path:
    local_appdata = os.getenv("LOCALAPPDATA")

    if local_appdata is not None:
        return Path(local_appdata) / YANDEX_BROWSER_PROFILE_RELATIVE_PATH

    return Path.home() / "AppData" / "Local" / YANDEX_BROWSER_PROFILE_RELATIVE_PATH


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
    error_message = normalize_error_message(text=str(error))
    browser_name = format_browser_display_name(browser_id=browser_id)

    if not error_message:
        return f"Не удалось создать cookies.txt из {browser_name}"

    if is_chrome_cookie_database_copy_error(error_message=error_message):
        return build_chromium_cookie_database_copy_error_message(
            browser_id=browser_id,
        )

    return f"Не удалось создать cookies.txt из {browser_name}: {error_message}"


def normalize_error_message(*, text: str) -> str:
    normalized_message = text.strip()

    while normalized_message.startswith("ERROR: "):
        normalized_message = normalized_message.removeprefix("ERROR: ").strip()

    return normalized_message


def is_chrome_cookie_database_copy_error(*, error_message: str) -> bool:
    return CHROME_COOKIE_DATABASE_COPY_ERROR_MARKER.casefold() in error_message.casefold()


def build_chromium_cookie_database_copy_error_message(*, browser_id: BrowserId) -> str:
    browser_name = format_browser_display_name(browser_id=browser_id)
    return (
        f"Не удалось создать cookies.txt из {browser_name}: браузер заблокировал базу cookies. "
        "Полностью закройте Chrome/Яндекс Браузер, включая фоновые процессы в трее "
        "или через Диспетчер задач, затем повторите попытку. "
        "Если ошибка повторяется, используйте Firefox или Opera."
    )


def format_browser_display_name(*, browser_id: BrowserId) -> str:
    return BROWSER_DISPLAY_NAMES.get(browser_id, browser_id.value)


def load_youtube_dl_browser_cookies_factory(
    *,
    runtime_manager: YtDlpRuntimeManager | None = None,
) -> YtDlpBrowserCookiesFactory:
    ytdlp_module = load_bundled_ytdlp_module() if runtime_manager is None else runtime_manager.load_module()
    return cast(YtDlpBrowserCookiesFactory, ytdlp_module.YoutubeDL)
