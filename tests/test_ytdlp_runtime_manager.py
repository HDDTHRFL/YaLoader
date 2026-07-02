from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from yaloader.application.dto.ytdlp_runtime import YtDlpRuntimeSource
from yaloader.infrastructure.ytdlp.runtime_manager import (
    YTDLP_IMPORT_NAME,
    YTDLP_RUNTIME_CURRENT_DIR_NAME,
    YTDLP_RUNTIME_ROOT_DIR_NAME,
    YtDlpRuntimeManager,
    build_ytdlp_runtime_scope_id,
    extract_ytdlp_module_version,
    has_external_ytdlp_runtime,
    load_bundled_ytdlp_module,
    load_ytdlp_module_from_path,
    remove_ytdlp_modules,
)


def test_build_ytdlp_runtime_scope_id_depends_on_executable_path(tmp_path: Path) -> None:
    first_scope_id = build_ytdlp_runtime_scope_id(executable_path=tmp_path / "YaLoader.exe")
    second_scope_id = build_ytdlp_runtime_scope_id(executable_path=tmp_path / "YaLoader2.exe")

    assert first_scope_id != second_scope_id
    assert len(first_scope_id) == 16


def test_has_external_ytdlp_runtime_detects_package_layout(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "current"
    package_dir = runtime_dir / "yt_dlp"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")

    assert has_external_ytdlp_runtime(runtime_dir=runtime_dir) is True


def test_has_external_ytdlp_runtime_rejects_missing_package(tmp_path: Path) -> None:
    assert has_external_ytdlp_runtime(runtime_dir=tmp_path / "current") is False


def test_extract_ytdlp_module_version_uses_version_submodule() -> None:
    module = ModuleType("yt_dlp")
    version_module = ModuleType("yt_dlp.version")
    version_module.__version__ = "2026.4.1"
    module.version = version_module

    assert extract_ytdlp_module_version(module=module) == "2026.4.1"


def test_runtime_manager_falls_back_to_bundled_without_external_runtime(tmp_path: Path) -> None:
    manager = YtDlpRuntimeManager(runtime_root_dir=tmp_path / "yt-dlp-runtimes")

    runtime_info = manager.get_runtime_info()

    assert runtime_info.source is YtDlpRuntimeSource.BUNDLED
    assert runtime_info.version


def test_remove_ytdlp_modules_removes_runtime_modules() -> None:
    sys.modules[YTDLP_IMPORT_NAME] = ModuleType(YTDLP_IMPORT_NAME)
    sys.modules[f"{YTDLP_IMPORT_NAME}.version"] = ModuleType(f"{YTDLP_IMPORT_NAME}.version")

    remove_ytdlp_modules()

    assert YTDLP_IMPORT_NAME not in sys.modules
    assert f"{YTDLP_IMPORT_NAME}.version" not in sys.modules


def test_load_bundled_ytdlp_module_reuses_loaded_bundled_module(monkeypatch: pytest.MonkeyPatch) -> None:
    module = ModuleType(YTDLP_IMPORT_NAME)
    module.__file__ = str(Path("C:/Python/site-packages/yt_dlp/__init__.py"))
    submodule = ModuleType(f"{YTDLP_IMPORT_NAME}.extractor")

    monkeypatch.setitem(sys.modules, YTDLP_IMPORT_NAME, module)
    monkeypatch.setitem(sys.modules, f"{YTDLP_IMPORT_NAME}.extractor", submodule)

    loaded_module = load_bundled_ytdlp_module()

    assert loaded_module is module
    assert sys.modules[YTDLP_IMPORT_NAME] is module
    assert sys.modules[f"{YTDLP_IMPORT_NAME}.extractor"] is submodule


def test_load_bundled_ytdlp_module_purges_loaded_external_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    external_runtime_dir = build_external_runtime_dir(root=tmp_path)
    external_module = ModuleType(YTDLP_IMPORT_NAME)
    external_module.__file__ = str(external_runtime_dir / YTDLP_IMPORT_NAME / "__init__.py")
    external_submodule_name = f"{YTDLP_IMPORT_NAME}.extractor"
    external_submodule = ModuleType(external_submodule_name)

    bundled_module = ModuleType(YTDLP_IMPORT_NAME)
    bundled_module.__file__ = str(tmp_path / "site-packages" / YTDLP_IMPORT_NAME / "__init__.py")

    monkeypatch.setitem(sys.modules, YTDLP_IMPORT_NAME, external_module)
    monkeypatch.setitem(sys.modules, external_submodule_name, external_submodule)
    monkeypatch.setattr(
        importlib,
        "import_module",
        build_fake_import_module(module=bundled_module),
    )

    loaded_module = load_bundled_ytdlp_module()

    assert loaded_module is bundled_module
    assert sys.modules[YTDLP_IMPORT_NAME] is bundled_module
    assert external_submodule_name not in sys.modules


def test_load_ytdlp_module_from_path_reuses_loaded_external_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original_sys_path = list(sys.path)
    external_runtime_dir = build_external_runtime_dir(root=tmp_path)
    external_module = ModuleType(YTDLP_IMPORT_NAME)
    external_module.__file__ = str(external_runtime_dir / YTDLP_IMPORT_NAME / "__init__.py")
    external_submodule_name = f"{YTDLP_IMPORT_NAME}.extractor"
    external_submodule = ModuleType(external_submodule_name)

    monkeypatch.setitem(sys.modules, YTDLP_IMPORT_NAME, external_module)
    monkeypatch.setitem(sys.modules, external_submodule_name, external_submodule)
    monkeypatch.setattr(
        importlib,
        "import_module",
        build_failing_import_module(),
    )

    try:
        loaded_module = load_ytdlp_module_from_path(runtime_dir=external_runtime_dir)

        assert loaded_module is external_module
        assert sys.modules[YTDLP_IMPORT_NAME] is external_module
        assert sys.modules[external_submodule_name] is external_submodule
        assert Path(sys.path[0]).resolve() == external_runtime_dir.resolve()
    finally:
        sys.path[:] = original_sys_path


def build_external_runtime_dir(*, root: Path) -> Path:
    return root / YTDLP_RUNTIME_ROOT_DIR_NAME / "scope" / YTDLP_RUNTIME_CURRENT_DIR_NAME


def build_fake_import_module(*, module: ModuleType):
    def fake_import_module(name: str) -> ModuleType:
        if name != YTDLP_IMPORT_NAME:
            raise AssertionError(f"Unexpected import: {name}")

        sys.modules[YTDLP_IMPORT_NAME] = module

        return module

    return fake_import_module


def build_failing_import_module():
    def fake_import_module(name: str) -> ModuleType:
        raise AssertionError(f"Module should already be loaded: {name}")

    return cast(object, fake_import_module)
