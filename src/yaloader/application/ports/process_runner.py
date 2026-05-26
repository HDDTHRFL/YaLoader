from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ProcessRunner(Protocol):
    def find_executable(self, executable_name: str) -> Path | None: ...
