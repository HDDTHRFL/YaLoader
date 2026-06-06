from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from yaloader.application.dto.tool_installation import (
    ToolId,
    ToolInstallationProgress,
    ToolInstallationResult,
)

ToolInstallationProgressCallback = Callable[[ToolInstallationProgress], None]


class ToolInstaller(Protocol):
    @property
    def tool_id(self) -> ToolId: ...

    def install(
        self,
        progress_callback: ToolInstallationProgressCallback | None = None,
    ) -> ToolInstallationResult: ...
