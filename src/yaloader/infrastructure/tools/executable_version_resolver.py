from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from yaloader.infrastructure.tools.version_detection import (
    normalize_tool_version,
    run_executable_for_text,
)


@dataclass(frozen=True, slots=True)
class ToolVersionCommand:
    args: tuple[str, ...]
    version_prefix: str = ""


TOOL_VERSION_COMMANDS: Final[dict[str, ToolVersionCommand]] = {
    "ffmpeg": ToolVersionCommand(args=("-version",)),
    "deno": ToolVersionCommand(args=("--version",)),
}


class ToolExecutableVersionResolutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ToolExecutableVersionResolver:
    def resolve_version(
        self,
        *,
        executable_path: Path,
        executable_name: str,
    ) -> str:
        normalized_name = normalize_tool_executable_name(executable_name=executable_name)
        command = TOOL_VERSION_COMMANDS.get(normalized_name)

        if command is None:
            raise ToolExecutableVersionResolutionError(f"получение версии не настроено для {executable_name}")

        version_text = run_executable_for_text(
            executable_path=executable_path,
            args=command.args,
        )

        return normalize_tool_version(
            text=version_text,
            prefix=command.version_prefix,
        )


def normalize_tool_executable_name(*, executable_name: str) -> str:
    normalized_name = executable_name.strip().casefold()

    if normalized_name.endswith(".exe"):
        normalized_name = normalized_name.removesuffix(".exe")

    return normalized_name
