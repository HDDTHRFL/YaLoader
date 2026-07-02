from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from zipfile import ZipFile

import pytest


def load_package_release_module() -> ModuleType:
    project_root = Path(__file__).resolve().parents[1]
    module_path = project_root / "scripts" / "package_release.py"
    module_name = "package_release_script"
    module_spec = importlib.util.spec_from_file_location(
        module_name,
        module_path,
    )

    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Could not load package_release.py: {module_path}")

    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)

    return module


package_release = load_package_release_module()


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

    assert package_release.read_project_version(pyproject_path=pyproject_path) == "1.2.3"


def test_read_project_version_rejects_missing_project_table(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text("[tool.ruff]\n", encoding="utf-8")

    with pytest.raises(package_release.PackageReleaseError):
        package_release.read_project_version(pyproject_path=pyproject_path)


def test_build_release_archive_path_uses_self_update_asset_name(tmp_path: Path) -> None:
    archive_path = package_release.build_release_archive_path(
        release_dir=tmp_path / "dist" / "release",
        version="1.2.3",
    )

    assert archive_path == tmp_path / "dist" / "release" / "YaLoader-v1.2.3-windows-x64.zip"


def test_create_release_archive_places_executable_at_archive_root(tmp_path: Path) -> None:
    executable_path = tmp_path / "dist" / "YaLoader.exe"
    executable_path.parent.mkdir(parents=True)
    executable_path.write_bytes(b"fake executable")

    archive_path = tmp_path / "dist" / "release" / "YaLoader-v1.2.3-windows-x64.zip"

    package_release.create_release_archive(
        executable_path=executable_path,
        archive_path=archive_path,
    )

    package_release.validate_release_archive(archive_path=archive_path)

    with ZipFile(archive_path) as archive:
        assert archive.namelist() == ["YaLoader.exe"]
        assert archive.read("YaLoader.exe") == b"fake executable"


def test_validate_release_archive_rejects_nested_executable(tmp_path: Path) -> None:
    archive_path = tmp_path / "YaLoader-v1.2.3-windows-x64.zip"

    with ZipFile(archive_path, mode="w") as archive:
        archive.writestr("nested/YaLoader.exe", b"fake executable")

    with pytest.raises(package_release.PackageReleaseError):
        package_release.validate_release_archive(archive_path=archive_path)


def test_calculate_file_sha256(tmp_path: Path) -> None:
    file_path = tmp_path / "file.bin"
    file_path.write_bytes(b"abc")

    assert package_release.calculate_file_sha256(file_path=file_path) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
