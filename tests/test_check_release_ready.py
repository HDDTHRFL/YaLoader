from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from zipfile import ZipFile

import pytest


def load_check_release_ready_module() -> ModuleType:
    project_root = Path(__file__).resolve().parents[1]
    module_path = project_root / "scripts" / "check_release_ready.py"
    module_name = "check_release_ready_script"
    module_spec = importlib.util.spec_from_file_location(
        module_name,
        module_path,
    )

    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Could not load check_release_ready.py: {module_path}")

    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)

    return module


check_release_ready = load_check_release_ready_module()


def test_read_project_version_from_pyproject(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """
[project]
name = "yaloader"
version = "1.2.3"
""".strip(),
        encoding="utf-8",
    )

    assert check_release_ready.read_project_version(pyproject_path=pyproject_path) == "1.2.3"


def test_validate_expected_version_accepts_matching_version() -> None:
    check_release_ready.validate_expected_version(
        actual_version="1.2.3",
        expected_version="1.2.3",
    )


def test_validate_expected_version_rejects_mismatched_version() -> None:
    with pytest.raises(check_release_ready.ReleaseReadinessError):
        check_release_ready.validate_expected_version(
            actual_version="1.2.3",
            expected_version="1.2.4",
        )


def test_build_expected_release_archive_path_uses_self_update_asset_name(tmp_path: Path) -> None:
    archive_path = check_release_ready.build_expected_release_archive_path(
        project_root=tmp_path,
        version="1.2.3",
    )

    assert archive_path == tmp_path / "dist" / "release" / "YaLoader-v1.2.3-windows-x64.zip"


def test_build_archive_checksum_path_uses_asset_name(tmp_path: Path) -> None:
    archive_path = tmp_path / "dist" / "release" / "YaLoader-v1.2.3-windows-x64.zip"

    assert check_release_ready.build_archive_checksum_path(archive_path=archive_path) == archive_path.with_name(
        "YaLoader-v1.2.3-windows-x64.zip.sha256"
    )


def test_validate_release_archive_accepts_required_root_files(tmp_path: Path) -> None:
    archive_path = tmp_path / "YaLoader-v1.2.3-windows-x64.zip"
    entries = {
        "YaLoader.exe": b"fake executable",
        "README.md": b"readme",
        "README_RU.md": "описание".encode(),
        "LICENSE": b"license",
    }
    checksum_text = "".join(
        f"{check_release_ready.calculate_bytes_sha256(value=content)}  {entry_name}\n"
        for entry_name, content in entries.items()
    )

    with ZipFile(archive_path, mode="w") as archive:
        for entry_name, content in entries.items():
            archive.writestr(entry_name, content)

        archive.writestr("SHA256SUMS.txt", checksum_text)

    check_release_ready.validate_release_archive(archive_path=archive_path)


def test_validate_release_archive_rejects_nested_executable(tmp_path: Path) -> None:
    archive_path = tmp_path / "YaLoader-v1.2.3-windows-x64.zip"

    with ZipFile(archive_path, mode="w") as archive:
        archive.writestr("nested/YaLoader.exe", b"fake executable")

    with pytest.raises(check_release_ready.ReleaseReadinessError):
        check_release_ready.validate_release_archive(archive_path=archive_path)


def test_parse_sha256sums_text_reads_valid_lines() -> None:
    checksums = check_release_ready.parse_sha256sums_text(
        text="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad  YaLoader.exe\n",
    )

    assert checksums == {
        "YaLoader.exe": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    }


def test_parse_sha256sums_text_rejects_invalid_digest() -> None:
    with pytest.raises(check_release_ready.ReleaseReadinessError):
        check_release_ready.parse_sha256sums_text(text="not-a-sha  YaLoader.exe\n")


def test_validate_archive_checksum_file_accepts_matching_hash(tmp_path: Path) -> None:
    archive_path = tmp_path / "YaLoader-v1.2.3-windows-x64.zip"
    checksum_path = tmp_path / "YaLoader-v1.2.3-windows-x64.zip.sha256"

    checksum_path.write_text(f"{'a' * 64}  {archive_path.name}\n", encoding="utf-8")

    check_release_ready.validate_archive_checksum_file(
        checksum_path=checksum_path,
        archive_path=archive_path,
        archive_sha256="a" * 64,
    )


def test_validate_archive_checksum_file_rejects_mismatched_hash(tmp_path: Path) -> None:
    archive_path = tmp_path / "YaLoader-v1.2.3-windows-x64.zip"
    checksum_path = tmp_path / "YaLoader-v1.2.3-windows-x64.zip.sha256"

    checksum_path.write_text(f"{'b' * 64}  {archive_path.name}\n", encoding="utf-8")

    with pytest.raises(check_release_ready.ReleaseReadinessError):
        check_release_ready.validate_archive_checksum_file(
            checksum_path=checksum_path,
            archive_path=archive_path,
            archive_sha256="a" * 64,
        )


def test_validate_github_release_description_file_accepts_asset_and_hash(tmp_path: Path) -> None:
    description_path = tmp_path / "GITHUB_RELEASE_DESCRIPTION-v1.2.3.md"
    description_path.write_text(
        f"Asset: YaLoader-v1.2.3-windows-x64.zip\nSHA-256: {'a' * 64}\n",
        encoding="utf-8",
    )

    check_release_ready.validate_github_release_description_file(
        description_path=description_path,
        asset_name="YaLoader-v1.2.3-windows-x64.zip",
        archive_sha256="a" * 64,
    )


def test_validate_github_release_description_file_rejects_missing_hash(tmp_path: Path) -> None:
    description_path = tmp_path / "GITHUB_RELEASE_DESCRIPTION-v1.2.3.md"
    description_path.write_text("Asset: YaLoader-v1.2.3-windows-x64.zip\n", encoding="utf-8")

    with pytest.raises(check_release_ready.ReleaseReadinessError):
        check_release_ready.validate_github_release_description_file(
            description_path=description_path,
            asset_name="YaLoader-v1.2.3-windows-x64.zip",
            archive_sha256="a" * 64,
        )


def test_calculate_file_sha256(tmp_path: Path) -> None:
    file_path = tmp_path / "file.bin"
    file_path.write_bytes(b"abc")

    assert check_release_ready.calculate_file_sha256(file_path=file_path) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
