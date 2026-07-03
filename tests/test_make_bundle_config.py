from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_make_bundle_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "make_bundle.py"
    spec = importlib.util.spec_from_file_location("yaloader_make_bundle_script", module_path)

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Не удалось загрузить модуль сборки бандла: {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


make_bundle_module = load_make_bundle_module()


def test_bundle_config_includes_license_file() -> None:
    config = make_bundle_module.BundleConfig()

    assert "LICENSE" in config.included_file_names


def test_bundle_config_excludes_temporary_debug_files() -> None:
    config = make_bundle_module.BundleConfig()

    assert ".tmp_*" in config.excluded_file_patterns
