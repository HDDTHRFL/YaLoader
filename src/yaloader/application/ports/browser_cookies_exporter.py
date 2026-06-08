from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from yaloader.application.dto.browser_cookies import (
    BrowserCookiesExportProgress,
    BrowserCookiesExportResult,
    BrowserId,
)

BrowserCookiesExportProgressCallback = Callable[[BrowserCookiesExportProgress], None]


class BrowserCookiesExporter(Protocol):
    def export(
        self,
        *,
        browser_id: BrowserId,
        target_file: Path,
        progress_callback: BrowserCookiesExportProgressCallback | None = None,
    ) -> BrowserCookiesExportResult: ...
