from __future__ import annotations

from typing import Protocol

from yaloader.application.dto.tool_installation import ToolId


class ToolVersionChecker(Protocol):
    @property
    def tool_id(self) -> ToolId: ...

    def get_current_version(self) -> str: ...

    def get_latest_version(self) -> str: ...
