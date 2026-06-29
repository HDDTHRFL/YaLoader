from __future__ import annotations

from typing import Protocol


class AppUpdateChecker(Protocol):
    def get_latest_version(self) -> str: ...
