from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Self, cast

import pytest

from yaloader.application.dto.browser_cookies import BrowserCookiesExportStatus, BrowserId
from yaloader.infrastructure.ytdlp.browser_cookies_exporter import (
    YtDlpBrowserCookiesExporter,
    YtDlpBrowserCookiesFactory,
    YtDlpBrowserCookiesOptions,
    build_browser_cookies_export_error_message,
    build_temporary_cookies_file,
    build_ytdlp_browser_cookie_options,
)


@dataclass(slots=True)
class FakeCookieJar:
    should_write_cookie_file: bool = True
    saved_file: Path | None = None
    save_call_count: int = 0
    ignore_discard: bool | None = None
    ignore_expires: bool | None = None

    def save(
        self,
        filename: str | None = None,
        ignore_discard: bool = False,
        ignore_expires: bool = False,
    ) -> None:
        self.save_call_count += 1
        self.ignore_discard = ignore_discard
        self.ignore_expires = ignore_expires

        if filename is None:
            return

        self.saved_file = Path(filename)

        if not self.should_write_cookie_file:
            return

        self.saved_file.write_text(
            "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tFALSE\t0\tSID\tfake\n",
            encoding="utf-8",
            newline="\n",
        )


@dataclass(slots=True)
class FakeYoutubeDLRuntime:
    options: YtDlpBrowserCookiesOptions
    should_write_cookie_file: bool = True
    cookiejar: FakeCookieJar = field(init=False)

    def __post_init__(self) -> None:
        self.cookiejar = FakeCookieJar(
            should_write_cookie_file=self.should_write_cookie_file,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return None


@dataclass(slots=True)
class FakeYoutubeDLFactory:
    should_write_cookie_file: bool = True
    calls: list[YtDlpBrowserCookiesOptions] = field(default_factory=list, init=False)
    runtimes: list[FakeYoutubeDLRuntime] = field(default_factory=list, init=False)

    def __call__(
        self,
        params: YtDlpBrowserCookiesOptions,
    ) -> FakeYoutubeDLRuntime:
        self.calls.append(params)
        runtime = FakeYoutubeDLRuntime(
            options=params,
            should_write_cookie_file=self.should_write_cookie_file,
        )
        self.runtimes.append(runtime)

        return runtime


def as_youtube_dl_factory(
    factory: FakeYoutubeDLFactory,
) -> YtDlpBrowserCookiesFactory:
    return cast(YtDlpBrowserCookiesFactory, factory)


def test_build_ytdlp_browser_cookie_options_uses_firefox_and_cookie_file(
    tmp_path: Path,
) -> None:
    cookie_file = tmp_path / "cookies.txt"

    options = build_ytdlp_browser_cookie_options(
        browser_id=BrowserId.FIREFOX,
        cookie_file=cookie_file,
    )

    assert options["cookiesfrombrowser"] == ("firefox", None, None, None)
    assert options["cookiefile"] == str(cookie_file)
    assert options["simulate"] is True


def test_build_ytdlp_browser_cookie_options_uses_opera_and_cookie_file(
    tmp_path: Path,
) -> None:
    cookie_file = tmp_path / "cookies.txt"

    options = build_ytdlp_browser_cookie_options(
        browser_id=BrowserId.OPERA,
        cookie_file=cookie_file,
    )

    assert options["cookiesfrombrowser"] == ("opera", None, None, None)
    assert options["cookiefile"] == str(cookie_file)
    assert options["simulate"] is True


def test_build_ytdlp_browser_cookie_options_uses_chrome_and_cookie_file(
    tmp_path: Path,
) -> None:
    cookie_file = tmp_path / "cookies.txt"

    options = build_ytdlp_browser_cookie_options(
        browser_id=BrowserId.CHROME,
        cookie_file=cookie_file,
    )

    assert options["cookiesfrombrowser"] == ("chrome", None, None, None)
    assert options["cookiefile"] == str(cookie_file)
    assert options["simulate"] is True


def test_build_ytdlp_browser_cookie_options_uses_yandex_profile_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_appdata = tmp_path / "LocalAppData"
    cookie_file = tmp_path / "cookies.txt"
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    options = build_ytdlp_browser_cookie_options(
        browser_id=BrowserId.YANDEX,
        cookie_file=cookie_file,
    )

    expected_profile_dir = local_appdata / "Yandex" / "YandexBrowser" / "User Data" / "Default"

    assert options["cookiesfrombrowser"] == (
        "chrome",
        str(expected_profile_dir),
        None,
        None,
    )
    assert options["cookiefile"] == str(cookie_file)
    assert options["simulate"] is True


def test_build_temporary_cookies_file_adds_tmp_suffix(tmp_path: Path) -> None:
    assert build_temporary_cookies_file(target_file=tmp_path / "cookies.txt") == (
        tmp_path / "cookies.txt.tmp"
    )


def test_ytdlp_browser_cookies_exporter_exports_firefox_cookies(tmp_path: Path) -> None:
    target_file = tmp_path / "cookies.txt"
    factory = FakeYoutubeDLFactory()
    progress_events = []

    exporter = YtDlpBrowserCookiesExporter(youtube_dl_factory=as_youtube_dl_factory(factory))

    result = exporter.export(
        browser_id=BrowserId.FIREFOX,
        target_file=target_file,
        progress_callback=progress_events.append,
    )

    runtime = factory.runtimes[0]

    assert result.status is BrowserCookiesExportStatus.EXPORTED
    assert result.cookies_file == target_file
    assert target_file.read_text(encoding="utf-8").startswith("# Netscape HTTP Cookie File")
    assert not build_temporary_cookies_file(target_file=target_file).exists()
    assert len(factory.calls) == 1
    assert factory.calls[0]["cookiesfrombrowser"] == ("firefox", None, None, None)
    assert runtime.cookiejar.save_call_count == 1
    assert runtime.cookiejar.saved_file == build_temporary_cookies_file(target_file=target_file)
    assert runtime.cookiejar.ignore_discard is True
    assert runtime.cookiejar.ignore_expires is True
    assert progress_events[-1].percent == 100
    assert progress_events[-1].path == target_file


def test_ytdlp_browser_cookies_exporter_replaces_existing_file(tmp_path: Path) -> None:
    target_file = tmp_path / "cookies.txt"
    target_file.write_text(
        "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tFALSE\t0\tOLD\told\n",
        encoding="utf-8",
    )

    exporter = YtDlpBrowserCookiesExporter(
        youtube_dl_factory=as_youtube_dl_factory(FakeYoutubeDLFactory())
    )

    result = exporter.export(
        browser_id=BrowserId.FIREFOX,
        target_file=target_file,
    )

    assert result.status is BrowserCookiesExportStatus.EXPORTED
    assert "SID\tfake" in target_file.read_text(encoding="utf-8")
    assert "OLD\told" not in target_file.read_text(encoding="utf-8")


def test_ytdlp_browser_cookies_exporter_reports_failure_when_cookie_file_was_not_created(
    tmp_path: Path,
) -> None:
    target_file = tmp_path / "cookies.txt"
    exporter = YtDlpBrowserCookiesExporter(
        youtube_dl_factory=as_youtube_dl_factory(
            FakeYoutubeDLFactory(should_write_cookie_file=False),
        ),
    )

    result = exporter.export(
        browser_id=BrowserId.FIREFOX,
        target_file=target_file,
    )

    assert result.status is BrowserCookiesExportStatus.FAILED
    assert result.cookies_file is None
    assert "Не удалось создать cookies.txt из Firefox" in result.message
    assert not target_file.exists()


def test_build_browser_cookies_export_error_message_explains_chrome_database_lock() -> None:
    message = build_browser_cookies_export_error_message(
        browser_id=BrowserId.CHROME,
        error=RuntimeError(
            "ERROR: ERROR: Could not copy Chrome cookie database. "
            "See https://github.com/yt-dlp/yt-dlp/issues/7271 for more info"
        ),
    )

    assert "браузер заблокировал базу cookies" in message
    assert "Полностью закройте Chrome/Яндекс Браузер" in message
    assert "Firefox или Opera" in message
