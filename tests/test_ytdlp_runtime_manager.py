from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

from yaloader.application.dto.ytdlp_runtime import YtDlpRuntimeSource
from yaloader.infrastructure.ytdlp.runtime_manager import (
    YTDLP_IMPORT_NAME,
    YtDlpRuntimeManager,
    build_ytdlp_runtime_scope_id,
    extract_ytdlp_module_version,
    has_external_ytdlp_runtime,
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
