from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ExecutableVersionResolver(Protocol):
    def resolve_version(
        self,
        *,
        executable_path: Path,
        executable_name: str,
    ) -> str: ...
