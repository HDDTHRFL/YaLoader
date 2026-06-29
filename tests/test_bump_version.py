from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def load_bump_version_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "bump_version.py"
    spec = importlib.util.spec_from_file_location("yaloader_bump_version_script", module_path)

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load bump_version script: {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


bump_version_module = load_bump_version_module()
bump_project_version = bump_version_module.bump_project_version
replace_project_version = bump_version_module.replace_project_version
validate_project_version = bump_version_module.validate_project_version
VersionBumpError = bump_version_module.VersionBumpError


def test_replace_project_version_updates_project_table_only() -> None:
    pyproject_text = '[project]\nname = "yaloader"\nversion = "0.1.0"\n\n[tool.demo]\nversion = "unchanged"\n'

    updated_text = replace_project_version(
        pyproject_text=pyproject_text,
        version="0.2.0",
    )

    assert 'version = "0.2.0"' in updated_text
    assert 'version = "unchanged"' in updated_text


def test_bump_project_version_updates_pyproject(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        ('[project]\nname = "yaloader"\nversion = "0.1.0"\n'),
        encoding="utf-8",
    )

    bump_project_version(project_root=tmp_path, version="0.2.0")

    assert 'version = "0.2.0"' in pyproject_path.read_text(encoding="utf-8")


def test_validate_project_version_rejects_invalid_version() -> None:
    with pytest.raises(VersionBumpError):
        validate_project_version(version="release-1")
