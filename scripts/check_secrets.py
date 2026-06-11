from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Final

MAX_SCANNED_FILE_SIZE_BYTES: Final = 5 * 1024 * 1024

EXCLUDED_DIR_NAMES: Final[frozenset[str]] = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "build",
        "dist",
        "_bundle",
        "downloads",
        "ffmpeg",
    }
)

TEXT_FILE_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        ".bat",
        ".cfg",
        ".cmd",
        ".css",
        ".html",
        ".ini",
        ".json",
        ".md",
        ".ps1",
        ".py",
        ".qss",
        ".spec",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)

TEXT_FILE_NAMES: Final[frozenset[str]] = frozenset(
    {
        ".gitattributes",
        ".gitignore",
        ".python-version",
    }
)

SENSITIVE_FILE_NAMES: Final[frozenset[str]] = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        "cookies.txt",
        "id_rsa",
        "id_ed25519",
        "private.key",
    }
)

SENSITIVE_FILE_PATTERNS: Final[tuple[str, ...]] = (
    "*.cookies.txt",
    "*cookies*.txt",
    "*.pem",
    "*.p12",
    "*.pfx",
    "*.key",
)

ALLOW_SECRET_LINE_MARKERS: Final[tuple[str, ...]] = (
    "pragma: allow-secret",
    "nosec",
)

PLACEHOLDER_VALUE_MARKERS: Final[tuple[str, ...]] = (
    "<",
    ">",
    "example",
    "sample",
    "dummy",
    "placeholder",
    "change_me",
    "changeme",
    "your_",
    "replace_me",
)


@dataclass(frozen=True, slots=True)
class ContentRule:
    rule_id: str
    message: str
    pattern: Pattern[str]


@dataclass(frozen=True, slots=True)
class SecretFinding:
    path: Path
    line_number: int
    column_number: int
    rule_id: str
    message: str
    preview: str


CONTENT_RULES: Final[tuple[ContentRule, ...]] = (
    ContentRule(
        rule_id="private-key",
        message="Найден приватный ключ.",
        pattern=re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    ),
    ContentRule(
        rule_id="github-token",
        message="Найден GitHub token.",
        pattern=re.compile(
            r"\b(?:(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}|"
            r"github_pat_[A-Za-z0-9_]{20,}_[A-Za-z0-9_]{20,})\b"
        ),
    ),
    ContentRule(
        rule_id="openai-token",
        message="Найден OpenAI-compatible API token.",
        pattern=re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    ),
    ContentRule(
        rule_id="google-api-key",
        message="Найден Google API key.",
        pattern=re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ),
    ContentRule(
        rule_id="aws-access-key",
        message="Найден AWS access key.",
        pattern=re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ),
    ContentRule(
        rule_id="telegram-bot-token",
        message="Найден Telegram bot token.",
        pattern=re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"),
    ),
)

GENERIC_SECRET_ASSIGNMENT_RE: Final[Pattern[str]] = re.compile(
    r"(?i)\b"
    r"(?P<name>"
    r"[a-z_][a-z0-9_-]*"
    r"(?:"
    r"api[_-]?key|"
    r"access[_-]?token|"
    r"refresh[_-]?token|"
    r"client[_-]?secret|"
    r"secret|"
    r"token|"
    r"password|"
    r"passwd"
    r")"
    r"[a-z0-9_-]*"
    r")"
    r"\b\s*[:=]\s*"
    r"(?P<quote>['\"]?)"
    r"(?P<value>[A-Za-z0-9_./+=-]{12,})"
    r"(?P=quote)"
)


def main(argv: Sequence[str] | None = None) -> int:
    parsed_args = parse_args(argv=argv)
    project_root = parsed_args.root.resolve()
    findings = check_project_secrets(project_root=project_root)

    if not findings:
        sys.stdout.write("Secret check passed.\n")
        return 0

    sys.stderr.write("Secret check failed.\n\n")

    for finding in findings:
        sys.stderr.write(format_finding(project_root=project_root, finding=finding))
        sys.stderr.write("\n")

    sys.stderr.write(
        "\nУдалите секреты из проекта или добавьте точечное исключение "
        "с комментарием 'pragma: allow-secret', "
        "если строка является безопасным тестовым примером.\n"
    )
    return 1


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan YaLoader project files for accidentally committed secrets.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory.",
    )

    return parser.parse_args(argv)


def check_project_secrets(*, project_root: Path) -> tuple[SecretFinding, ...]:
    findings: list[SecretFinding] = []

    for file_path in collect_project_files(project_root=project_root):
        relative_path = file_path.relative_to(project_root)

        findings.extend(find_sensitive_file_path_findings(relative_path=relative_path))

        if not should_scan_text_content(file_path=file_path):
            continue

        findings.extend(scan_text_file(project_root=project_root, file_path=file_path))

    return tuple(findings)


def collect_project_files(*, project_root: Path) -> tuple[Path, ...]:
    files: list[Path] = []

    for file_path in project_root.rglob("*"):
        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(project_root)

        if has_excluded_directory(relative_path=relative_path):
            continue

        files.append(file_path)

    return tuple(sorted(files, key=lambda path: path.relative_to(project_root).as_posix()))


def has_excluded_directory(*, relative_path: Path) -> bool:
    return any(path_part in EXCLUDED_DIR_NAMES for path_part in relative_path.parts[:-1])


def find_sensitive_file_path_findings(*, relative_path: Path) -> tuple[SecretFinding, ...]:
    file_name = relative_path.name.casefold()

    if file_name in SENSITIVE_FILE_NAMES or matches_sensitive_file_pattern(file_name=file_name):
        return (
            SecretFinding(
                path=relative_path,
                line_number=1,
                column_number=1,
                rule_id="sensitive-file",
                message="В проекте найден файл, который обычно содержит секреты.",
                preview=relative_path.as_posix(),
            ),
        )

    return ()


def matches_sensitive_file_pattern(*, file_name: str) -> bool:
    return any(
        fnmatch.fnmatchcase(file_name, pattern.casefold()) for pattern in SENSITIVE_FILE_PATTERNS
    )


def should_scan_text_content(*, file_path: Path) -> bool:
    if file_path.name in TEXT_FILE_NAMES:
        return True

    if file_path.suffix.casefold() not in TEXT_FILE_SUFFIXES:
        return False

    try:
        return file_path.stat().st_size <= MAX_SCANNED_FILE_SIZE_BYTES
    except OSError:
        return False


def scan_text_file(*, project_root: Path, file_path: Path) -> tuple[SecretFinding, ...]:
    relative_path = file_path.relative_to(project_root)

    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ()

    findings: list[SecretFinding] = []

    for line_number, line in enumerate(lines, start=1):
        if should_skip_line(line=line):
            continue

        findings.extend(
            scan_line_with_specific_rules(
                relative_path=relative_path,
                line_number=line_number,
                line=line,
            )
        )
        findings.extend(
            scan_line_for_generic_secret_assignment(
                relative_path=relative_path,
                line_number=line_number,
                line=line,
            )
        )

    return tuple(findings)


def should_skip_line(*, line: str) -> bool:
    normalized_line = line.casefold()
    return any(marker in normalized_line for marker in ALLOW_SECRET_LINE_MARKERS)


def scan_line_with_specific_rules(
    *,
    relative_path: Path,
    line_number: int,
    line: str,
) -> tuple[SecretFinding, ...]:
    findings: list[SecretFinding] = []

    for rule in CONTENT_RULES:
        for match in rule.pattern.finditer(line):
            findings.append(
                SecretFinding(
                    path=relative_path,
                    line_number=line_number,
                    column_number=match.start() + 1,
                    rule_id=rule.rule_id,
                    message=rule.message,
                    preview=build_redacted_preview(line=line, span=match.span()),
                )
            )

    return tuple(findings)


def scan_line_for_generic_secret_assignment(
    *,
    relative_path: Path,
    line_number: int,
    line: str,
) -> tuple[SecretFinding, ...]:
    findings: list[SecretFinding] = []

    for match in GENERIC_SECRET_ASSIGNMENT_RE.finditer(line):
        secret_value = match.group("value")

        if is_placeholder_secret_value(value=secret_value):
            continue

        findings.append(
            SecretFinding(
                path=relative_path,
                line_number=line_number,
                column_number=match.start("value") + 1,
                rule_id="generic-secret-assignment",
                message="Найдено подозрительное присваивание секрета.",
                preview=build_redacted_preview(line=line, span=match.span("value")),
            )
        )

    return tuple(findings)


def is_placeholder_secret_value(*, value: str) -> bool:
    normalized_value = value.strip().casefold()

    if len(normalized_value) < 12:
        return True

    if len(set(normalized_value)) <= 3:
        return True

    return any(marker in normalized_value for marker in PLACEHOLDER_VALUE_MARKERS)


def build_redacted_preview(*, line: str, span: tuple[int, int]) -> str:
    start, end = span
    preview = f"{line[:start]}<redacted>{line[end:]}".strip()

    if len(preview) <= 160:
        return preview

    return f"{preview[:157]}..."


def format_finding(*, project_root: Path, finding: SecretFinding) -> str:
    display_path = finding.path.as_posix()

    absolute_path = project_root / finding.path

    if absolute_path.exists():
        display_path = absolute_path.relative_to(project_root).as_posix()

    return (
        f"{display_path}:{finding.line_number}:{finding.column_number}: "
        f"{finding.rule_id}: {finding.message} {finding.preview}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
