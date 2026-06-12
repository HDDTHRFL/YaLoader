from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_check_secrets_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "check_secrets.py"
    spec = importlib.util.spec_from_file_location("yaloader_check_secrets_script", module_path)

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Не удалось загрузить модуль проверки секретов: {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


check_secrets_module = load_check_secrets_module()
check_project_secrets = check_secrets_module.check_project_secrets
format_finding = check_secrets_module.format_finding


def test_check_project_secrets_passes_for_clean_project(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        'APP_NAME = "YaLoader"\n',
        encoding="utf-8",
    )

    assert check_project_secrets(project_root=tmp_path) == ()


def test_check_project_secrets_detects_sensitive_file_name(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("APP_NAME=YaLoader\n", encoding="utf-8")

    findings = check_project_secrets(project_root=tmp_path)

    assert len(findings) == 1
    assert findings[0].rule_id == "sensitive-file"
    assert findings[0].path == Path(".env")


def test_check_project_secrets_detects_private_key(tmp_path: Path) -> None:
    private_key_text = build_private_key_fixture()
    (tmp_path / "key.txt").write_text(private_key_text, encoding="utf-8")

    findings = check_project_secrets(project_root=tmp_path)

    assert len(findings) == 1
    assert findings[0].rule_id == "private-key"
    assert "<redacted>" in findings[0].preview


def test_check_project_secrets_detects_generic_secret_assignment(tmp_path: Path) -> None:
    sensitive_value = build_sensitive_value()
    (tmp_path / "settings.py").write_text(
        f'SERVICE_TOKEN = "{sensitive_value}"\n',
        encoding="utf-8",
    )

    findings = check_project_secrets(project_root=tmp_path)

    assert len(findings) == 1
    assert findings[0].rule_id == "generic-secret-assignment"
    assert sensitive_value not in findings[0].preview
    assert "<redacted>" in findings[0].preview


def test_check_project_secrets_detects_typed_generic_secret_assignment(tmp_path: Path) -> None:
    sensitive_value = build_sensitive_value()
    (tmp_path / "settings.py").write_text(
        f'SERVICE_TOKEN: str = "{sensitive_value}"\n',
        encoding="utf-8",
    )

    findings = check_project_secrets(project_root=tmp_path)

    assert len(findings) == 1
    assert findings[0].rule_id == "generic-secret-assignment"
    assert sensitive_value not in findings[0].preview


def test_check_project_secrets_ignores_python_cancellation_token_annotations(
    tmp_path: Path,
) -> None:
    (tmp_path / "downloader.py").write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                "def download(",
                "    *,",
                "    cancellation_token: CancellationToken | None = None,",
                ") -> None:",
                "    cancellation_token = DownloadCancellationToken()",
                "    run(cancellation_token=cancellation_token)",
                "",
            )
        ),
        encoding="utf-8",
    )

    assert check_project_secrets(project_root=tmp_path) == ()


def test_check_project_secrets_ignores_python_code_references(tmp_path: Path) -> None:
    (tmp_path / "test_module.py").write_text(
        "\n".join(
            (
                "check_secrets_module = load_check_secrets_module()",
                "check_project_secrets = check_secrets_module.check_project_secrets",
                "",
            )
        ),
        encoding="utf-8",
    )

    assert check_project_secrets(project_root=tmp_path) == ()


def test_check_project_secrets_ignores_placeholder_values(tmp_path: Path) -> None:
    (tmp_path / "settings.py").write_text(
        'SERVICE_TOKEN = "your_token_here"\n',
        encoding="utf-8",
    )

    assert check_project_secrets(project_root=tmp_path) == ()


def test_check_project_secrets_ignores_allowed_secret_test_line(tmp_path: Path) -> None:
    sensitive_value = build_sensitive_value()
    (tmp_path / "settings.py").write_text(
        f'SERVICE_TOKEN = "{sensitive_value}"  # pragma: allow-secret\n',
        encoding="utf-8",
    )

    assert check_project_secrets(project_root=tmp_path) == ()


def test_check_project_secrets_ignores_excluded_directories(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "_bundle"
    bundle_dir.mkdir()
    (bundle_dir / "cookies.txt").write_text("secret", encoding="utf-8")

    assert check_project_secrets(project_root=tmp_path) == ()


def test_format_finding_uses_relative_path(tmp_path: Path) -> None:
    sensitive_value = build_sensitive_value()
    file_path = tmp_path / "settings.py"
    file_path.write_text(f'SERVICE_TOKEN = "{sensitive_value}"\n', encoding="utf-8")
    findings = check_project_secrets(project_root=tmp_path)

    formatted_finding = format_finding(project_root=tmp_path, finding=findings[0])

    assert formatted_finding.startswith("settings.py:1:")
    assert sensitive_value not in formatted_finding


def build_sensitive_value() -> str:
    return "production" + "TokenValue12345"


def build_private_key_fixture() -> str:
    begin_marker = "-----BEGIN " + "PRIVATE KEY-----"
    end_marker = "-----END " + "PRIVATE KEY-----"

    return f"{begin_marker}\nabc\n{end_marker}\n"
