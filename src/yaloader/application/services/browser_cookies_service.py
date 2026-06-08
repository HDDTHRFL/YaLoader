from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yaloader.application.dto.browser_cookies import BrowserCookiesExportResult, BrowserId
from yaloader.application.ports.browser_cookies_exporter import (
    BrowserCookiesExporter,
    BrowserCookiesExportProgressCallback,
)


@dataclass(frozen=True, slots=True)
class BrowserCookiesService:
    exporter: BrowserCookiesExporter
    target_file: Path

    def export_from_browser(
        self,
        *,
        browser_id: BrowserId,
        progress_callback: BrowserCookiesExportProgressCallback | None = None,
    ) -> BrowserCookiesExportResult:
        return self.exporter.export(
            browser_id=browser_id,
            target_file=self.target_file,
            progress_callback=progress_callback,
        )
