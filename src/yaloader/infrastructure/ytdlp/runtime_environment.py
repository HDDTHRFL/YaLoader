from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Final, Protocol

from loguru import logger

PATH_ENVIRONMENT_VARIABLE: Final = "PATH"
YTDLP_RUNTIME_EXECUTABLE_NAMES: Final[tuple[str, ...]] = (
    "deno",
    "ffmpeg",
)

_path_environment_lock = RLock()


class ExecutableLocator(Protocol):
    def find_executable(self, executable_name: str) -> Path | None: ...


@dataclass(frozen=True, slots=True)
class YtDlpRuntimeEnvironment:
    process_runner: ExecutableLocator | None = None

    @contextmanager
    def apply(self) -> Iterator[None]:
        executable_dirs = collect_ytdlp_runtime_executable_dirs(
            process_runner=self.process_runner,
        )

        with extend_process_path(executable_dirs=executable_dirs):
            yield


def collect_ytdlp_runtime_executable_dirs(
    *,
    process_runner: ExecutableLocator | None,
) -> tuple[Path, ...]:
    if process_runner is None:
        return ()

    executable_dirs: list[Path] = []
    normalized_dirs: set[str] = set()

    for executable_name in YTDLP_RUNTIME_EXECUTABLE_NAMES:
        executable_path = process_runner.find_executable(executable_name)

        if executable_path is None:
            continue

        executable_dir = executable_path.parent

        if not executable_dir.is_dir():
            continue

        normalized_dir = normalize_path_for_environment(path=executable_dir)

        if normalized_dir in normalized_dirs:
            continue

        normalized_dirs.add(normalized_dir)
        executable_dirs.append(executable_dir)

    return tuple(executable_dirs)


@contextmanager
def extend_process_path(*, executable_dirs: tuple[Path, ...]) -> Iterator[None]:
    if not executable_dirs:
        yield
        return

    with _path_environment_lock:
        previous_path = os.environ.get(PATH_ENVIRONMENT_VARIABLE, "")
        extended_path = build_extended_path(
            executable_dirs=executable_dirs,
            previous_path=previous_path,
        )

        if extended_path == previous_path:
            yield
            return

        logger.debug(
            "Temporarily extending PATH for yt-dlp runtime. dirs={}",
            tuple(str(directory) for directory in executable_dirs),
        )

        os.environ[PATH_ENVIRONMENT_VARIABLE] = extended_path

        try:
            yield
        finally:
            os.environ[PATH_ENVIRONMENT_VARIABLE] = previous_path


def build_extended_path(*, executable_dirs: tuple[Path, ...], previous_path: str) -> str:
    existing_parts = tuple(part for part in previous_path.split(os.pathsep) if part)
    normalized_seen_parts: set[str] = set()
    result_parts: list[str] = []

    for executable_dir in executable_dirs:
        normalized_dir = normalize_path_for_environment(path=executable_dir)

        if normalized_dir in normalized_seen_parts:
            continue

        normalized_seen_parts.add(normalized_dir)
        result_parts.append(str(executable_dir.resolve()))

    for existing_part in existing_parts:
        normalized_existing_part = normalize_raw_path_for_environment(value=existing_part)

        if normalized_existing_part in normalized_seen_parts:
            continue

        normalized_seen_parts.add(normalized_existing_part)
        result_parts.append(existing_part)

    return os.pathsep.join(result_parts)


def normalize_path_for_environment(*, path: Path) -> str:
    return normalize_raw_path_for_environment(value=str(path.resolve()))


def normalize_raw_path_for_environment(*, value: str) -> str:
    return value.strip().rstrip("\\/").casefold()
