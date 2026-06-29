from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Final

VERSION_RE: Final = re.compile(r"\d+(?:\.\d+){1,3}")
VERSION_COMMAND_TIMEOUT_SECONDS: Final = 10.0


class ToolVersionDetectionError(RuntimeError):
    pass


def run_executable_for_text(*, executable_path: Path, args: tuple[str, ...]) -> str:
    try:
        completed_process = subprocess.run(
            (str(executable_path), *args),
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=VERSION_COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ToolVersionDetectionError(f"не удалось получить версию: {executable_path}: {error}") from error

    output = "\n".join(part.strip() for part in (completed_process.stdout, completed_process.stderr) if part.strip())

    if not output:
        raise ToolVersionDetectionError(f"команда версии не вернула вывод: {executable_path}")

    return output


def normalize_tool_version(*, text: str, prefix: str = "") -> str:
    match = VERSION_RE.search(text)

    if match is None:
        raise ToolVersionDetectionError(f"не удалось определить версию из текста: {text!r}")

    version = match.group(0)
    return f"{prefix}{version}"


def is_version_newer(*, candidate_version: str, current_version: str) -> bool:
    return parse_version_parts(candidate_version) > parse_version_parts(current_version)


def parse_version_parts(version: str) -> tuple[int, ...]:
    normalized_version = normalize_tool_version(text=version)
    return tuple(int(part) for part in normalized_version.split("."))
