from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from zipfile import BadZipFile, ZipFile

from yaloader.application.dto.app_update import (
    YALOADER_EXE_FILE_NAME,
    build_yaloader_windows_x64_archive_name,
)

PYPROJECT_FILE_NAME: Final = "pyproject.toml"
DIST_DIR_NAME: Final = "dist"
RELEASE_DIR_NAME: Final = "release"
FILE_READ_CHUNK_SIZE_BYTES: Final = 1024 * 1024


class ReleaseReadinessError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ReleaseReadinessResult:
    version: str
    archive_path: Path
    archive_sha256: str

    @property
    def asset_name(self) -> str:
        return self.archive_path.name


def main(argv: Sequence[str] | None = None) -> int:
    parsed_args = parse_args(argv=argv)

    try:
        result = check_release_ready(
            project_root=parsed_args.root.resolve(),
            expected_version=parsed_args.expected_version,
            skip_verify=parsed_args.skip_verify,
        )
    except ReleaseReadinessError as error:
        sys.stderr.write(f"Release readiness check failed: {error}\n")
        return 1

    print_release_readiness_result(result=result)
    return 0


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check that the YaLoader release archive is ready for GitHub Release upload.",
    )
    parser.add_argument(
        "expected_version",
        nargs="?",
        help="Expected project version, for example 1.1.0.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip tools\\verify_project.bat during the readiness check.",
    )

    return parser.parse_args(argv)


def check_release_ready(
    *,
    project_root: Path,
    expected_version: str | None = None,
    skip_verify: bool = False,
) -> ReleaseReadinessResult:
    ensure_git_worktree_clean(project_root=project_root, stage="before verification")

    version = read_project_version(pyproject_path=project_root / PYPROJECT_FILE_NAME)
    validate_expected_version(
        actual_version=version,
        expected_version=expected_version,
    )

    if not skip_verify:
        run_project_verification(project_root=project_root)

    ensure_git_worktree_clean(project_root=project_root, stage="after verification")

    archive_path = build_expected_release_archive_path(
        project_root=project_root,
        version=version,
    )
    validate_release_archive_path(
        archive_path=archive_path,
        version=version,
    )
    validate_release_archive(archive_path=archive_path)
    archive_sha256 = calculate_file_sha256(file_path=archive_path)

    return ReleaseReadinessResult(
        version=version,
        archive_path=archive_path,
        archive_sha256=archive_sha256,
    )


def read_project_version(*, pyproject_path: Path) -> str:
    if not pyproject_path.is_file():
        raise ReleaseReadinessError(f"{PYPROJECT_FILE_NAME} not found: {pyproject_path}")

    try:
        pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ReleaseReadinessError(f"could not read {PYPROJECT_FILE_NAME}: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise ReleaseReadinessError(f"could not parse {PYPROJECT_FILE_NAME}: {error}") from error

    project_table = pyproject_data.get("project")

    if not isinstance(project_table, dict):
        raise ReleaseReadinessError(f"{PYPROJECT_FILE_NAME} does not contain [project] table")

    version = project_table.get("version")

    if not isinstance(version, str) or not version.strip():
        raise ReleaseReadinessError(f"{PYPROJECT_FILE_NAME} does not contain a valid project version")

    return version.strip()


def validate_expected_version(
    *,
    actual_version: str,
    expected_version: str | None,
) -> None:
    if expected_version is None:
        return

    normalized_expected_version = expected_version.strip()

    if actual_version == normalized_expected_version:
        return

    raise ReleaseReadinessError(
        f"project version mismatch: expected {normalized_expected_version}, actual {actual_version}"
    )


def run_project_verification(*, project_root: Path) -> None:
    verify_script = project_root / "tools" / "verify_project.bat"

    if not verify_script.is_file():
        raise ReleaseReadinessError(f"verification script not found: {verify_script}")

    run_command(
        project_root=project_root,
        command=("cmd.exe", "/c", str(verify_script)),
        description="project verification",
    )


def ensure_git_worktree_clean(*, project_root: Path, stage: str) -> None:
    result = run_command(
        project_root=project_root,
        command=("git", "status", "--porcelain"),
        description=f"git status {stage}",
    )
    dirty_lines = tuple(line for line in result.stdout.splitlines() if line.strip())

    if not dirty_lines:
        return

    preview = "\n".join(dirty_lines[:20])
    raise ReleaseReadinessError(f"Git worktree is not clean {stage}. Commit or revert changes first.\n{preview}")


def build_expected_release_archive_path(*, project_root: Path, version: str) -> Path:
    return project_root / DIST_DIR_NAME / RELEASE_DIR_NAME / build_yaloader_windows_x64_archive_name(version=version)


def validate_release_archive_path(*, archive_path: Path, version: str) -> None:
    expected_asset_name = build_yaloader_windows_x64_archive_name(version=version)

    if archive_path.name != expected_asset_name:
        raise ReleaseReadinessError(
            f"release archive asset name mismatch: expected {expected_asset_name}, actual {archive_path.name}"
        )

    if not archive_path.is_file():
        raise ReleaseReadinessError(f"release archive not found: {archive_path}. Run tools\\package_release.bat first.")


def validate_release_archive(*, archive_path: Path) -> None:
    try:
        with ZipFile(archive_path) as archive:
            names = tuple(archive.namelist())
    except BadZipFile as error:
        raise ReleaseReadinessError(f"release archive is not a valid zip file: {archive_path}") from error

    if YALOADER_EXE_FILE_NAME not in names:
        raise ReleaseReadinessError(f"{YALOADER_EXE_FILE_NAME} not found at archive root: {archive_path}")

    executable_entries = tuple(
        name for name in names if Path(name).name.casefold() == YALOADER_EXE_FILE_NAME.casefold()
    )

    if executable_entries != (YALOADER_EXE_FILE_NAME,):
        raise ReleaseReadinessError(
            f"release archive must contain exactly one root {YALOADER_EXE_FILE_NAME}: {executable_entries}"
        )


def calculate_file_sha256(*, file_path: Path) -> str:
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(FILE_READ_CHUNK_SIZE_BYTES):
            digest.update(chunk)

    return digest.hexdigest()


def run_command(
    *,
    project_root: Path,
    command: Sequence[str],
    description: str,
) -> subprocess.CompletedProcess[str]:
    completed_process = subprocess.run(
        tuple(command),
        cwd=project_root,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        text=True,
    )

    if completed_process.returncode != 0:
        command_text = " ".join(command)
        error_text = (completed_process.stderr or completed_process.stdout).strip()
        if not error_text:
            error_text = f"exit code {completed_process.returncode}"

        raise ReleaseReadinessError(f"{description} failed: {command_text}\n{error_text}")

    return completed_process


def print_release_readiness_result(*, result: ReleaseReadinessResult) -> None:
    sys.stdout.write("\nRelease readiness check passed.\n")
    sys.stdout.write(f"Version:    {result.version}\n")
    sys.stdout.write(f"Archive:    {result.archive_path}\n")
    sys.stdout.write(f"Asset name: {result.asset_name}\n")
    sys.stdout.write(f"SHA-256:    {result.archive_sha256}\n")
    sys.stdout.write("\nUse this asset name and SHA-256 in the GitHub Release.\n")


if __name__ == "__main__":
    raise SystemExit(main())
