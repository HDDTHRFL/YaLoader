from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from yaloader.application.dto.ytdlp_runtime_update import (
    YtDlpRuntimeUpdateProgress,
    YtDlpRuntimeUpdateResult,
)

YtDlpRuntimeUpdateProgressCallback = Callable[[YtDlpRuntimeUpdateProgress], None]


class YtDlpRuntimeInstaller(Protocol):
    def install_latest(
        self,
        progress_callback: YtDlpRuntimeUpdateProgressCallback | None = None,
    ) -> YtDlpRuntimeUpdateResult: ...
