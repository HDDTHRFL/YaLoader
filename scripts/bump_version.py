from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from re import Pattern
from typing import Final

PROJECT_TABLE_HEADER: Final = "[project]"
PYPROJECT_FILE_NAME: Final = "pyproject.toml"

VERSION_LINE_RE: Final[Pattern[str]] = re.compile(
    r'^(?P<prefix>\s*version\s*=\s*)"(?P<version>[^"]+)"(?P<suffix>\s*(?:#.*)?)$'
)
VERSION_RE: Final[Pattern[str]] = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:(?:a|b|rc)(0|[1-9]\d*)|\.post(0|[1-9]\d*)|\.dev(0|[1-9]\d*))?$"
)


class VersionBumpError(RuntimeError):
    pass


def main(argv: Sequence[str] | None = None) -> int:
    parsed_args = parse_args(argv=argv)

    try:
        bump_project_version(
            project_root=parsed_args.root.resolve(),
            version=parsed_args.version,
        )
    except VersionBumpError as error:
        sys.stderr.write(f"Version bump failed: {error}\n")
        return 1

    sys.stdout.write(f"Project version bumped to {parsed_args.version}.\n")
    return 0


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update the YaLoader project version in pyproject.toml.",
    )
    parser.add_argument(
        "version",
        help="New release version, for example 0.2.0.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory.",
    )

    return parser.parse_args(argv)


def bump_project_version(*, project_root: Path, version: str) -> None:
    validate_project_version(version=version)

    pyproject_path = project_root / PYPROJECT_FILE_NAME

    if not pyproject_path.is_file():
        raise VersionBumpError(f"{PYPROJECT_FILE_NAME} not found: {pyproject_path}")

    try:
        pyproject_text = pyproject_path.read_text(encoding="utf-8")
    except OSError as error:
        raise VersionBumpError(f"could not read {PYPROJECT_FILE_NAME}: {error}") from error

    updated_text = replace_project_version(
        pyproject_text=pyproject_text,
        version=version,
    )

    try:
        pyproject_path.write_text(updated_text, encoding="utf-8", newline="\n")
    except OSError as error:
        raise VersionBumpError(f"could not write {PYPROJECT_FILE_NAME}: {error}") from error


def validate_project_version(*, version: str) -> None:
    if VERSION_RE.fullmatch(version) is None:
        raise VersionBumpError("version must look like 0.2.0, 0.2.0rc1, 0.2.0.post1, or 0.2.0.dev1")


def replace_project_version(*, pyproject_text: str, version: str) -> str:
    lines = pyproject_text.splitlines(keepends=True)
    is_project_table = False

    for line_index, line in enumerate(lines):
        stripped_line = line.strip()

        if stripped_line == PROJECT_TABLE_HEADER:
            is_project_table = True
            continue

        if is_project_table and stripped_line.startswith("[") and stripped_line.endswith("]"):
            break

        if not is_project_table:
            continue

        line_without_newline = line.rstrip("\r\n")
        newline = line[len(line_without_newline) :]
        version_match = VERSION_LINE_RE.fullmatch(line_without_newline)

        if version_match is None:
            continue

        lines[line_index] = f'{version_match.group("prefix")}"{version}"{version_match.group("suffix")}{newline}'
        return "".join(lines)

    raise VersionBumpError("could not find [project] version in pyproject.toml")


if __name__ == "__main__":
    raise SystemExit(main())
