from __future__ import annotations

import shutil
from pathlib import Path

from yaloader.config.paths import AppPaths

WINDOWS_EXECUTABLE_SUFFIX = ".exe"


class ToolLocatorProcessRunner:
    def __init__(self, *, paths: AppPaths) -> None:
        self._paths = paths

    def find_executable(self, executable_name: str) -> Path | None:
        app_managed_executable = self._find_app_managed_executable(
            executable_name=executable_name,
        )

        if app_managed_executable is not None:
            return app_managed_executable

        system_executable = shutil.which(executable_name)

        if system_executable is None:
            return None

        return Path(system_executable)

    def _find_app_managed_executable(self, *, executable_name: str) -> Path | None:
        normalized_name = normalize_executable_name(executable_name=executable_name)
        candidate = self._build_app_managed_candidate(executable_name=normalized_name)

        if candidate is None or not candidate.is_file():
            return None

        return candidate

    def _build_app_managed_candidate(self, *, executable_name: str) -> Path | None:
        candidates = {
            "ffmpeg.exe": self._paths.ffmpeg_executable,
            "deno.exe": self._paths.deno_executable,
        }

        return candidates.get(executable_name)


def normalize_executable_name(*, executable_name: str) -> str:
    normalized_name = executable_name.strip().casefold()

    if normalized_name.endswith(WINDOWS_EXECUTABLE_SUFFIX):
        return normalized_name

    return f"{normalized_name}{WINDOWS_EXECUTABLE_SUFFIX}"
