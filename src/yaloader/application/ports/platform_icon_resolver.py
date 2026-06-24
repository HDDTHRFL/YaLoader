from __future__ import annotations

from pathlib import Path
from typing import Protocol


class PlatformIconResolver(Protocol):
    def resolve_icon_path(self, *, url: str) -> Path | None: ...
