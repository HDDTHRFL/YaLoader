from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

WINDOWS_EXECUTABLE_SUFFIX = ".exe"


@dataclass(frozen=True, slots=True)
class ToolSearchPaths:
    app_tools_dir: Path

    @property
    def ffmpeg_executable(self) -> Path:
        return self.app_tools_dir / "ffmpeg" / "bin" / "ffmpeg.exe"

    @property
    def deno_executable(self) -> Path:
        return self.app_tools_dir / "deno" / "deno.exe"


class ToolLocatorProcessRunner:
    def __init__(self, *, search_paths: ToolSearchPaths) -> None:
        self._search_paths = search_paths

    def find_executable(self, executable_name: str) -> Path | None:
        bundled_executable = self._find_app_managed_executable(
            executable_name=executable_name,
        )

        if bundled_executable is not None:
            return bundled_executable

        system_executable = shutil.which(executable_name)

        if system_executable is None:
            return None

        return Path(system_executable)

    def _find_app_managed_executable(self, *, executable_name: str) -> Path | None:
        normalized_name = normalize_executable_name(executable_name=executable_name)

        candidates = {
            "ffmpeg.exe": self._search_paths.ffmpeg_executable,
            "deno.exe": self._search_paths.deno_executable,
        }

        candidate = candidates.get(normalized_name)

        if candidate is None or not candidate.is_file():
            return None

        return candidate


def normalize_executable_name(*, executable_name: str) -> str:
    normalized_name = executable_name.strip().casefold()

    if normalized_name.endswith(WINDOWS_EXECUTABLE_SUFFIX):
        return normalized_name

    return f"{normalized_name}{WINDOWS_EXECUTABLE_SUFFIX}"
