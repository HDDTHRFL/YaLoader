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
SHA256_HEX_LENGTH: Final = 64

RELEASE_ARCHIVE_INCLUDED_ROOT_FILES: Final[tuple[str, ...]] = (
    "README.md",
    "README_RU.md",
    "LICENSE",
)
RELEASE_ARCHIVE_CHECKSUMS_FILE_NAME: Final = "SHA256SUMS.txt"
RELEASE_ARCHIVE_REQUIRED_ENTRIES: Final[tuple[str, ...]] = (
    YALOADER_EXE_FILE_NAME,
    *RELEASE_ARCHIVE_INCLUDED_ROOT_FILES,
    RELEASE_ARCHIVE_CHECKSUMS_FILE_NAME,
)
ARCHIVE_CHECKSUM_FILE_SUFFIX: Final = ".sha256"
GITHUB_RELEASE_DESCRIPTION_FILE_NAME_TEMPLATE: Final = "GITHUB_RELEASE_DESCRIPTION-v{version}.md"


class ReleaseReadinessError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ReleaseReadinessResult:
    version: str
    archive_path: Path
    archive_sha256: str
    archive_checksum_path: Path
    github_release_description_path: Path

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
    archive_checksum_path = build_archive_checksum_path(archive_path=archive_path)
    github_release_description_path = build_github_release_description_path(
        release_dir=archive_path.parent,
        version=version,
    )

    validate_archive_checksum_file(
        checksum_path=archive_checksum_path,
        archive_path=archive_path,
        archive_sha256=archive_sha256,
    )
    validate_github_release_description_file(
        description_path=github_release_description_path,
        asset_name=archive_path.name,
        archive_sha256=archive_sha256,
    )

    return ReleaseReadinessResult(
        version=version,
        archive_path=archive_path,
        archive_sha256=archive_sha256,
        archive_checksum_path=archive_checksum_path,
        github_release_description_path=github_release_description_path,
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


def build_archive_checksum_path(*, archive_path: Path) -> Path:
    return archive_path.with_name(f"{archive_path.name}{ARCHIVE_CHECKSUM_FILE_SUFFIX}")


def build_github_release_description_path(*, release_dir: Path, version: str) -> Path:
    return release_dir / GITHUB_RELEASE_DESCRIPTION_FILE_NAME_TEMPLATE.format(version=version)


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

            missing_entries = tuple(
                entry_name for entry_name in RELEASE_ARCHIVE_REQUIRED_ENTRIES if entry_name not in names
            )

            if missing_entries:
                raise ReleaseReadinessError(f"release archive misses required entries: {missing_entries}")

            executable_entries = tuple(
                name for name in names if Path(name).name.casefold() == YALOADER_EXE_FILE_NAME.casefold()
            )

            if executable_entries != (YALOADER_EXE_FILE_NAME,):
                raise ReleaseReadinessError(
                    f"release archive must contain exactly one root {YALOADER_EXE_FILE_NAME}: {executable_entries}"
                )

            validate_archive_entry_checksums(
                archive=archive,
                required_entry_names=RELEASE_ARCHIVE_REQUIRED_ENTRIES[:-1],
            )
    except BadZipFile as error:
        raise ReleaseReadinessError(f"release archive is not a valid zip file: {archive_path}") from error


def validate_archive_entry_checksums(
    *,
    archive: ZipFile,
    required_entry_names: Sequence[str],
) -> None:
    checksum_text = archive.read(RELEASE_ARCHIVE_CHECKSUMS_FILE_NAME).decode("utf-8")
    checksums = parse_sha256sums_text(text=checksum_text)

    for entry_name in required_entry_names:
        expected_sha256 = checksums.get(entry_name)

        if expected_sha256 is None:
            raise ReleaseReadinessError(f"{RELEASE_ARCHIVE_CHECKSUMS_FILE_NAME} does not contain {entry_name}")

        actual_sha256 = calculate_bytes_sha256(value=archive.read(entry_name))

        if actual_sha256 != expected_sha256:
            raise ReleaseReadinessError(
                f"archive checksum mismatch for {entry_name}: expected {expected_sha256}, actual {actual_sha256}"
            )


def parse_sha256sums_text(*, text: str) -> dict[str, str]:
    checksums: dict[str, str] = {}

    for raw_line in text.splitlines():
        normalized_line = raw_line.strip()

        if not normalized_line:
            continue

        parts = normalized_line.split(maxsplit=1)

        if len(parts) != 2:
            raise ReleaseReadinessError(f"invalid SHA256SUMS line: {raw_line!r}")

        digest, entry_name = parts
        normalized_entry_name = entry_name.strip()

        if not is_sha256_hex_digest(value=digest):
            raise ReleaseReadinessError(f"invalid SHA-256 digest for {normalized_entry_name}: {digest}")

        checksums[normalized_entry_name] = digest.casefold()

    return checksums


def validate_archive_checksum_file(
    *,
    checksum_path: Path,
    archive_path: Path,
    archive_sha256: str,
) -> None:
    if not checksum_path.is_file():
        raise ReleaseReadinessError(f"archive checksum file not found: {checksum_path}")

    try:
        checksum_text = checksum_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ReleaseReadinessError(f"could not read archive checksum file: {checksum_path}") from error

    checksums = parse_sha256sums_text(text=checksum_text)
    expected_sha256 = checksums.get(archive_path.name)

    if expected_sha256 is None:
        raise ReleaseReadinessError(f"archive checksum file does not contain {archive_path.name}")

    if expected_sha256 != archive_sha256:
        raise ReleaseReadinessError(
            f"archive checksum file mismatch: expected {archive_sha256}, actual {expected_sha256}"
        )


def validate_github_release_description_file(
    *,
    description_path: Path,
    asset_name: str,
    archive_sha256: str,
) -> None:
    if not description_path.is_file():
        raise ReleaseReadinessError(f"GitHub release description file not found: {description_path}")

    try:
        description_text = description_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ReleaseReadinessError(f"could not read GitHub release description: {description_path}") from error

    if asset_name not in description_text:
        raise ReleaseReadinessError(f"GitHub release description does not mention asset name: {asset_name}")

    if archive_sha256 not in description_text:
        raise ReleaseReadinessError("GitHub release description does not mention archive SHA-256")


def is_sha256_hex_digest(*, value: str) -> bool:
    if len(value) != SHA256_HEX_LENGTH:
        return False

    return all(character in "0123456789abcdefABCDEF" for character in value)


def calculate_file_sha256(*, file_path: Path) -> str:
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(FILE_READ_CHUNK_SIZE_BYTES):
            digest.update(chunk)

    return digest.hexdigest()


def calculate_bytes_sha256(*, value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
    sys.stdout.write(f"Version:              {result.version}\n")
    sys.stdout.write(f"Archive:              {result.archive_path}\n")
    sys.stdout.write(f"Asset name:           {result.asset_name}\n")
    sys.stdout.write(f"Archive checksum:     {result.archive_checksum_path}\n")
    sys.stdout.write(f"GitHub description:   {result.github_release_description_path}\n")
    sys.stdout.write(f"SHA-256:              {result.archive_sha256}\n")
    sys.stdout.write("\nUse this asset name and SHA-256 in the GitHub Release.\n")


if __name__ == "__main__":
    raise SystemExit(main())
