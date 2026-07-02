from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from zipfile import ZIP_DEFLATED, ZipFile

from yaloader.application.dto.app_update import (
    YALOADER_EXE_FILE_NAME,
    build_yaloader_windows_x64_archive_name,
)

PYPROJECT_FILE_NAME: Final = "pyproject.toml"
DIST_DIR_NAME: Final = "dist"
BUILD_DIR_NAME: Final = "build"
RELEASE_DIR_NAME: Final = "release"
PYINSTALLER_SPEC_PATH: Final = Path("specs") / "yaloader.spec"
FILE_READ_CHUNK_SIZE_BYTES: Final = 1024 * 1024


class PackageReleaseError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PackageReleaseResult:
    version: str
    executable_path: Path
    archive_path: Path
    archive_sha256: str

    @property
    def asset_name(self) -> str:
        return self.archive_path.name


def main(argv: Sequence[str] | None = None) -> int:
    parsed_args = parse_args(argv=argv)

    try:
        result = package_release(
            project_root=parsed_args.root.resolve(),
            skip_verify=parsed_args.skip_verify,
        )
    except PackageReleaseError as error:
        sys.stderr.write(f"Release packaging failed: {error}\n")
        return 1

    print_package_release_result(result=result)
    return 0


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build YaLoader.exe and create a GitHub Release archive.",
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
        help="Skip tools\\verify_project.bat before packaging.",
    )

    return parser.parse_args(argv)


def package_release(*, project_root: Path, skip_verify: bool = False) -> PackageReleaseResult:
    version = read_project_version(pyproject_path=project_root / PYPROJECT_FILE_NAME)

    if not skip_verify:
        run_project_verification(project_root=project_root)

    clean_build_artifacts(project_root=project_root)
    run_pyinstaller(project_root=project_root)

    executable_path = project_root / DIST_DIR_NAME / YALOADER_EXE_FILE_NAME

    if not executable_path.is_file():
        raise PackageReleaseError(f"PyInstaller did not create executable: {executable_path}")

    release_dir = project_root / DIST_DIR_NAME / RELEASE_DIR_NAME
    archive_path = build_release_archive_path(
        release_dir=release_dir,
        version=version,
    )

    create_release_archive(
        executable_path=executable_path,
        archive_path=archive_path,
    )
    validate_release_archive(archive_path=archive_path)
    archive_sha256 = calculate_file_sha256(file_path=archive_path)

    return PackageReleaseResult(
        version=version,
        executable_path=executable_path,
        archive_path=archive_path,
        archive_sha256=archive_sha256,
    )


def read_project_version(*, pyproject_path: Path) -> str:
    if not pyproject_path.is_file():
        raise PackageReleaseError(f"{PYPROJECT_FILE_NAME} not found: {pyproject_path}")

    try:
        pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise PackageReleaseError(f"could not read {PYPROJECT_FILE_NAME}: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise PackageReleaseError(f"could not parse {PYPROJECT_FILE_NAME}: {error}") from error

    project_table = pyproject_data.get("project")

    if not isinstance(project_table, dict):
        raise PackageReleaseError(f"{PYPROJECT_FILE_NAME} does not contain [project] table")

    version = project_table.get("version")

    if not isinstance(version, str) or not version.strip():
        raise PackageReleaseError(f"{PYPROJECT_FILE_NAME} does not contain a valid project version")

    return version.strip()


def build_release_archive_path(*, release_dir: Path, version: str) -> Path:
    archive_name = build_yaloader_windows_x64_archive_name(version=version)

    return release_dir / archive_name


def run_project_verification(*, project_root: Path) -> None:
    verify_script = project_root / "tools" / "verify_project.bat"

    if not verify_script.is_file():
        raise PackageReleaseError(f"verification script not found: {verify_script}")

    run_command(
        project_root=project_root,
        command=("cmd.exe", "/c", str(verify_script)),
        description="project verification",
    )


def clean_build_artifacts(*, project_root: Path) -> None:
    remove_directory_if_exists(directory_path=project_root / BUILD_DIR_NAME)
    remove_directory_if_exists(directory_path=project_root / DIST_DIR_NAME)


def run_pyinstaller(*, project_root: Path) -> None:
    spec_path = project_root / PYINSTALLER_SPEC_PATH

    if not spec_path.is_file():
        raise PackageReleaseError(f"PyInstaller spec not found: {spec_path}")

    run_command(
        project_root=project_root,
        command=(
            "uv",
            "run",
            "pyinstaller",
            "--noconfirm",
            "--clean",
            str(PYINSTALLER_SPEC_PATH),
        ),
        description="PyInstaller build",
    )


def create_release_archive(*, executable_path: Path, archive_path: Path) -> None:
    if not executable_path.is_file():
        raise PackageReleaseError(f"executable not found: {executable_path}")

    archive_path.parent.mkdir(parents=True, exist_ok=True)

    if archive_path.exists():
        archive_path.unlink()

    with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        archive.write(
            filename=executable_path,
            arcname=YALOADER_EXE_FILE_NAME,
        )


def validate_release_archive(*, archive_path: Path) -> None:
    if not archive_path.is_file():
        raise PackageReleaseError(f"release archive not found: {archive_path}")

    with ZipFile(archive_path) as archive:
        names = tuple(archive.namelist())

    if YALOADER_EXE_FILE_NAME not in names:
        raise PackageReleaseError(f"{YALOADER_EXE_FILE_NAME} not found in release archive: {archive_path}")

    unexpected_executables = tuple(
        name for name in names if Path(name).name.casefold() == YALOADER_EXE_FILE_NAME.casefold()
    )

    if unexpected_executables != (YALOADER_EXE_FILE_NAME,):
        raise PackageReleaseError(
            f"release archive must contain exactly one root {YALOADER_EXE_FILE_NAME}: {unexpected_executables}"
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
) -> None:
    completed_process = subprocess.run(
        tuple(command),
        cwd=project_root,
        check=False,
    )

    if completed_process.returncode != 0:
        command_text = " ".join(command)
        raise PackageReleaseError(f"{description} failed with exit code {completed_process.returncode}: {command_text}")


def remove_directory_if_exists(*, directory_path: Path) -> None:
    if directory_path.exists():
        shutil.rmtree(directory_path)


def print_package_release_result(*, result: PackageReleaseResult) -> None:
    sys.stdout.write("\nRelease package created successfully.\n")
    sys.stdout.write(f"Version:       {result.version}\n")
    sys.stdout.write(f"Executable:    {result.executable_path}\n")
    sys.stdout.write(f"Archive:       {result.archive_path}\n")
    sys.stdout.write(f"Asset name:    {result.asset_name}\n")
    sys.stdout.write(f"SHA-256:       {result.archive_sha256}\n")
    sys.stdout.write("\nUpload this file to GitHub Release assets:\n")
    sys.stdout.write(f"{result.archive_path}\n")


if __name__ == "__main__":
    raise SystemExit(main())
