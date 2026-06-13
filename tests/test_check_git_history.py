from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_check_git_history_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "check_git_history.py"
    spec = importlib.util.spec_from_file_location(
        "yaloader_check_git_history_script",
        module_path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load check_git_history script: {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


check_git_history_module = load_check_git_history_module()
matches_any_path_pattern = check_git_history_module.matches_any_path_pattern
parse_git_grep_line = check_git_history_module.parse_git_grep_line
parse_git_grep_output = check_git_history_module.parse_git_grep_output


def test_matches_any_path_pattern_checks_file_name_and_path() -> None:
    assert matches_any_path_pattern(
        path="nested/private.key",
        patterns=("*.key",),
    )
    assert matches_any_path_pattern(
        path="_bundle/project_yaloader_bundle.txt",
        patterns=("_bundle/*",),
    )
    assert not matches_any_path_pattern(
        path="src/yaloader/main.py",
        patterns=("*.key",),
    )


def test_parse_git_grep_line_parses_windows_path_with_colons() -> None:
    parsed_line = parse_git_grep_line(
        raw_line="abc123:src/yaloader/example.py:10:api_key = 'replace_me'",
    )

    assert parsed_line == (
        "abc123",
        "src/yaloader/example.py",
        10,
        "api_key = 'replace_me'",
    )


def test_parse_git_grep_output_detects_private_key_marker() -> None:
    private_key_marker = "-----BEGIN " + "PRIVATE KEY-----"
    findings = parse_git_grep_output(
        output=f"abc123:secret.txt:1:{private_key_marker}\n",
    )

    assert len(findings) == 1
    assert findings[0].rule_id == "private-key"
    assert findings[0].preview == "<redacted>"


def test_parse_git_grep_output_ignores_placeholder_secret_assignment() -> None:
    findings = parse_git_grep_output(
        output='abc123:example.py:1:api_key = "replace_me_with_real_value"\n',
    )

    assert findings == ()
