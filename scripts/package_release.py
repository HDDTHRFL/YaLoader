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


class PackageReleaseError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PackageReleaseResult:
    version: str
    executable_path: Path
    archive_path: Path
    archive_sha256: str
    archive_checksum_path: Path
    github_release_description_path: Path

    @property
    def asset_name(self) -> str:
        return self.archive_path.name


@dataclass(frozen=True, slots=True)
class ReleaseArchiveEntry:
    source_path: Path
    archive_name: str


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
        project_root=project_root,
        executable_path=executable_path,
        archive_path=archive_path,
    )
    validate_release_archive(archive_path=archive_path)

    archive_sha256 = calculate_file_sha256(file_path=archive_path)
    archive_checksum_path = write_archive_checksum_file(
        archive_path=archive_path,
        archive_sha256=archive_sha256,
    )
    github_release_description_path = write_github_release_description_file(
        release_dir=release_dir,
        version=version,
        asset_name=archive_path.name,
        archive_sha256=archive_sha256,
    )

    return PackageReleaseResult(
        version=version,
        executable_path=executable_path,
        archive_path=archive_path,
        archive_sha256=archive_sha256,
        archive_checksum_path=archive_checksum_path,
        github_release_description_path=github_release_description_path,
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


def build_archive_checksum_path(*, archive_path: Path) -> Path:
    return archive_path.with_name(f"{archive_path.name}{ARCHIVE_CHECKSUM_FILE_SUFFIX}")


def build_github_release_description_path(*, release_dir: Path, version: str) -> Path:
    return release_dir / GITHUB_RELEASE_DESCRIPTION_FILE_NAME_TEMPLATE.format(version=version)


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


def create_release_archive(
    *,
    project_root: Path,
    executable_path: Path,
    archive_path: Path,
) -> None:
    entries = build_release_archive_entries(
        project_root=project_root,
        executable_path=executable_path,
    )
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    if archive_path.exists():
        archive_path.unlink()

    with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in entries:
            archive.write(
                filename=entry.source_path,
                arcname=entry.archive_name,
            )

        archive.writestr(
            zinfo_or_arcname=RELEASE_ARCHIVE_CHECKSUMS_FILE_NAME,
            data=build_archive_entry_checksums_text(entries=entries),
        )


def build_release_archive_entries(*, project_root: Path, executable_path: Path) -> tuple[ReleaseArchiveEntry, ...]:
    if not executable_path.is_file():
        raise PackageReleaseError(f"executable not found: {executable_path}")

    entries: list[ReleaseArchiveEntry] = [
        ReleaseArchiveEntry(
            source_path=executable_path,
            archive_name=YALOADER_EXE_FILE_NAME,
        )
    ]

    for file_name in RELEASE_ARCHIVE_INCLUDED_ROOT_FILES:
        source_path = project_root / file_name

        if not source_path.is_file():
            raise PackageReleaseError(f"release file not found: {source_path}")

        entries.append(
            ReleaseArchiveEntry(
                source_path=source_path,
                archive_name=file_name,
            )
        )

    return tuple(entries)


def build_archive_entry_checksums_text(*, entries: Sequence[ReleaseArchiveEntry]) -> str:
    lines = [f"{calculate_file_sha256(file_path=entry.source_path)}  {entry.archive_name}" for entry in entries]

    return "\n".join(lines) + "\n"


def validate_release_archive(*, archive_path: Path) -> None:
    if not archive_path.is_file():
        raise PackageReleaseError(f"release archive not found: {archive_path}")

    with ZipFile(archive_path) as archive:
        names = tuple(archive.namelist())

        missing_entries = tuple(
            entry_name for entry_name in RELEASE_ARCHIVE_REQUIRED_ENTRIES if entry_name not in names
        )

        if missing_entries:
            raise PackageReleaseError(f"release archive misses required entries: {missing_entries}")

        unexpected_executables = tuple(
            name for name in names if Path(name).name.casefold() == YALOADER_EXE_FILE_NAME.casefold()
        )

        if unexpected_executables != (YALOADER_EXE_FILE_NAME,):
            raise PackageReleaseError(
                f"release archive must contain exactly one root {YALOADER_EXE_FILE_NAME}: {unexpected_executables}"
            )

        validate_archive_entry_checksums(
            archive=archive,
            required_entry_names=RELEASE_ARCHIVE_REQUIRED_ENTRIES[:-1],
        )


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
            raise PackageReleaseError(f"{RELEASE_ARCHIVE_CHECKSUMS_FILE_NAME} does not contain {entry_name}")

        actual_sha256 = calculate_bytes_sha256(value=archive.read(entry_name))

        if actual_sha256 != expected_sha256:
            raise PackageReleaseError(
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
            raise PackageReleaseError(f"invalid SHA256SUMS line: {raw_line!r}")

        digest, entry_name = parts
        normalized_entry_name = entry_name.strip()

        if not is_sha256_hex_digest(value=digest):
            raise PackageReleaseError(f"invalid SHA-256 digest for {normalized_entry_name}: {digest}")

        checksums[normalized_entry_name] = digest.casefold()

    return checksums


def is_sha256_hex_digest(*, value: str) -> bool:
    if len(value) != SHA256_HEX_LENGTH:
        return False

    return all(character in "0123456789abcdefABCDEF" for character in value)


def write_archive_checksum_file(*, archive_path: Path, archive_sha256: str) -> Path:
    checksum_path = build_archive_checksum_path(archive_path=archive_path)
    checksum_path.write_text(
        f"{archive_sha256}  {archive_path.name}\n",
        encoding="utf-8",
        newline="\n",
    )

    return checksum_path


def write_github_release_description_file(
    *,
    release_dir: Path,
    version: str,
    asset_name: str,
    archive_sha256: str,
) -> Path:
    description_path = build_github_release_description_path(
        release_dir=release_dir,
        version=version,
    )
    description_path.write_text(
        build_github_release_description(
            version=version,
            asset_name=asset_name,
            archive_sha256=archive_sha256,
        ),
        encoding="utf-8",
        newline="\n",
    )

    return description_path


def build_github_release_description(
    *,
    version: str,
    asset_name: str,
    archive_sha256: str,
) -> str:
    archive_contents = "\n".join(f"- `{entry_name}`" for entry_name in RELEASE_ARCHIVE_REQUIRED_ENTRIES)

    return (
        f"# YaLoader v{version}\n"
        "\n"
        "## What's changed\n"
        "\n"
        "- Improved VK Audio link handling, including unsupported public catalog audio links. "
        "Such links are now rejected before they are added to the queue and the app shows a clear warning message.\n"
        "- Improved VK Audio diagnostics and probing stability for regular track links.\n"
        "- Improved queue input validation and status bar feedback.\n"
        "- Improved release packaging: the archive now contains the executable, user documentation, "
        "license, and checksums.\n"
        "- Added a dedicated release readiness check before publishing to GitHub Releases.\n"
        "- Improved application restart stability after self-update in PyInstaller builds.\n"
        "\n"
        "## Release asset\n"
        "\n"
        f"- Asset: `{asset_name}`\n"
        f"- SHA-256: `{archive_sha256}`\n"
        "\n"
        "## Archive contents\n"
        "\n"
        f"{archive_contents}\n"
        "\n"
        "## Installation\n"
        "\n"
        "1. Download the archive from GitHub Release assets.\n"
        "2. Extract the archive into a separate folder.\n"
        "3. Run `YaLoader.exe`.\n"
        "4. On first launch, check the system status block and prepare FFmpeg/Deno if the app asks for it.\n"
        "\n"
        "## Important\n"
        "\n"
        "- Windows may show a SmartScreen warning because the build may not be digitally signed.\n"
        "- Do not publish or share your `cookies.txt` file.\n"
        "- For content that requires account access, use an up-to-date `cookies.txt` exported from your browser.\n"
        "- VK Audio public catalog links of the `audio-200...` form are currently not supported. "
        "Use a regular track link copied from your own audio list instead.\n"
    )


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
    sys.stdout.write(f"Version:              {result.version}\n")
    sys.stdout.write(f"Executable:           {result.executable_path}\n")
    sys.stdout.write(f"Archive:              {result.archive_path}\n")
    sys.stdout.write(f"Asset name:           {result.asset_name}\n")
    sys.stdout.write(f"Archive checksum:     {result.archive_checksum_path}\n")
    sys.stdout.write(f"GitHub description:   {result.github_release_description_path}\n")
    sys.stdout.write(f"SHA-256:              {result.archive_sha256}\n")
    sys.stdout.write("\nUpload this file to GitHub Release assets:\n")
    sys.stdout.write(f"{result.archive_path}\n")
    sys.stdout.write("\nCopy this file content to GitHub Release description:\n")
    sys.stdout.write(f"{result.github_release_description_path}\n")


if __name__ == "__main__":
    raise SystemExit(main())
