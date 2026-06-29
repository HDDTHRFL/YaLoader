from __future__ import annotations

from typing import Protocol

from yaloader.application.dto.ytdlp_runtime import YtDlpRuntimeInfo


class YtDlpRuntimeInfoProvider(Protocol):
    def get_runtime_info(self) -> YtDlpRuntimeInfo: ...


class YtDlpRuntimeResetter(Protocol):
    def reset_external_runtime(self) -> bool: ...
