from __future__ import annotations

import shutil
from pathlib import Path


class SystemProcessRunner:
    def find_executable(self, executable_name: str) -> Path | None:
        executable_path = shutil.which(executable_name)

        if executable_path is None:
            return None

        return Path(executable_path)
