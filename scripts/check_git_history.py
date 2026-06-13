from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Final

GIT_BATCH_SIZE: Final = 40

SENSITIVE_HISTORY_PATH_PATTERNS: Final[tuple[str, ...]] = (
    ".env",
    ".env.*",
    "cookies.txt",
    "*.cookies.txt",
    "*cookies*.txt",
    "*.pem",
    "*.p12",
    "*.pfx",
    "*.key",
    "id_rsa",
    "id_ed25519",
    "private.key",
)

GENERATED_HISTORY_PATH_PATTERNS: Final[tuple[str, ...]] = (
    "_bundle/*",
    "build/*",
    "dist/*",
    "downloads/*",
    "ffmpeg/*",
    "*.log",
    "*.tmp",
    "*.bak",
    "project_yaloader_bundle*",
)

TEXT_PATHSPECS: Final[tuple[str, ...]] = (
    "*.bat",
    "*.cfg",
    "*.cmd",
    "*.css",
    "*.html",
    "*.ini",
    "*.json",
    "*.md",
    "*.ps1",
    "*.py",
    "*.qss",
    "*.spec",
    "*.toml",
    "*.txt",
    "*.yaml",
    "*.yml",
    ".gitattributes",
    ".gitignore",
    ".python-version",
    "LICENSE",
)

SECRET_KEYWORD_GREP_PATTERN: Final = (
    "api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|"
    "secret|token|password|passwd|PRIVATE KEY|ghp_|gho_|ghu_|ghs_|ghr_|"
    "github_pat_|sk-|AIza|AKIA|ASIA"
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

CODE_REFERENCE_VALUE_RE: Final[Pattern[str]] = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$"
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
    r"\b"
    r"(?:\s*:\s*[^:=#,\n]+)?"
    r"\s*(?P<operator>[:=])\s*"
    r"(?P<quote>['\"]?)"
    r"(?P<value>[A-Za-z0-9_./+=-]{12,})"
    r"(?P=quote)"
)


@dataclass(frozen=True, slots=True)
class ContentRule:
    rule_id: str
    message: str
    pattern: Pattern[str]


@dataclass(frozen=True, slots=True)
class GitHistoryFinding:
    commit: str | None
    path: str
    line_number: int | None
    rule_id: str
    message: str
    preview: str


CONTENT_RULES: Final[tuple[ContentRule, ...]] = (
    ContentRule(
        rule_id="private-key",
        message="В истории Git найден приватный ключ.",
        pattern=re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    ),
    ContentRule(
        rule_id="github-token",
        message="В истории Git найден GitHub token.",
        pattern=re.compile(
            r"\b(?:(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}|"
            r"github_pat_[A-Za-z0-9_]{20,}_[A-Za-z0-9_]{20,})\b"
        ),
    ),
    ContentRule(
        rule_id="openai-token",
        message="В истории Git найден OpenAI-compatible API token.",
        pattern=re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    ),
    ContentRule(
        rule_id="google-api-key",
        message="В истории Git найден Google API key.",
        pattern=re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ),
    ContentRule(
        rule_id="aws-access-key",
        message="В истории Git найден AWS access key.",
        pattern=re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ),
    ContentRule(
        rule_id="telegram-bot-token",
        message="В истории Git найден Telegram bot token.",
        pattern=re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"),
    ),
)


class GitHistoryCheckError(RuntimeError):
    pass


def main(argv: Sequence[str] | None = None) -> int:
    parsed_args = parse_args(argv=argv)
    project_root = parsed_args.root.resolve()

    try:
        findings = check_git_history(project_root=project_root)
    except GitHistoryCheckError as error:
        sys.stderr.write(f"Git history check failed: {error}\n")
        return 1

    if not findings:
        sys.stdout.write("Git history check passed.\n")
        return 0

    sys.stderr.write("Git history check failed.\n\n")

    for finding in findings:
        sys.stderr.write(format_finding(finding=finding))
        sys.stderr.write("\n")

    sys.stderr.write(
        "\nПеред публикацией на GitHub нужно убрать эти данные из истории "
        "или осознанно решить, что найденные записи безопасны.\n"
    )
    return 1


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan YaLoader Git history for secrets and generated files.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory.",
    )

    return parser.parse_args(argv)


def check_git_history(*, project_root: Path) -> tuple[GitHistoryFinding, ...]:
    ensure_git_repository(project_root=project_root)

    sys.stdout.write("Collecting Git history paths...\n")
    sys.stdout.flush()
    history_paths = collect_git_history_paths(project_root=project_root)

    findings: list[GitHistoryFinding] = []
    findings.extend(find_sensitive_history_paths(paths=history_paths))
    findings.extend(find_generated_history_paths(paths=history_paths))

    sys.stdout.write("Scanning Git history content with git grep...\n")
    sys.stdout.flush()
    findings.extend(scan_history_content_with_git_grep(project_root=project_root))

    return tuple(deduplicate_findings(findings=findings))


def ensure_git_repository(*, project_root: Path) -> None:
    result = run_git(
        project_root=project_root,
        args=("rev-parse", "--is-inside-work-tree"),
        allow_failure=True,
    )

    if result.returncode != 0 or result.stdout.strip() != "true":
        raise GitHistoryCheckError(f"not a Git repository: {project_root}")


def collect_git_history_paths(*, project_root: Path) -> tuple[str, ...]:
    result = run_git(
        project_root=project_root,
        args=("log", "--all", "--name-only", "--pretty=format:"),
    )
    paths = {normalize_git_path(path=line) for line in result.stdout.splitlines() if line.strip()}

    return tuple(sorted(paths))


def find_sensitive_history_paths(*, paths: tuple[str, ...]) -> tuple[GitHistoryFinding, ...]:
    return tuple(
        GitHistoryFinding(
            commit=None,
            path=path,
            line_number=None,
            rule_id="sensitive-history-path",
            message="В истории Git найден путь, похожий на секретный файл.",
            preview=path,
        )
        for path in paths
        if matches_any_path_pattern(
            path=path,
            patterns=SENSITIVE_HISTORY_PATH_PATTERNS,
        )
    )


def find_generated_history_paths(*, paths: tuple[str, ...]) -> tuple[GitHistoryFinding, ...]:
    return tuple(
        GitHistoryFinding(
            commit=None,
            path=path,
            line_number=None,
            rule_id="generated-history-path",
            message="В истории Git найден служебный или сгенерированный файл.",
            preview=path,
        )
        for path in paths
        if matches_any_path_pattern(
            path=path,
            patterns=GENERATED_HISTORY_PATH_PATTERNS,
        )
    )


def scan_history_content_with_git_grep(*, project_root: Path) -> tuple[GitHistoryFinding, ...]:
    commits = collect_git_commits(project_root=project_root)

    if not commits:
        return ()

    findings: list[GitHistoryFinding] = []

    for commit_batch in iter_batches(items=commits, batch_size=GIT_BATCH_SIZE):
        result = run_git(
            project_root=project_root,
            args=(
                "grep",
                "-I",
                "-n",
                "--no-color",
                "-E",
                SECRET_KEYWORD_GREP_PATTERN,
                *commit_batch,
                "--",
                *TEXT_PATHSPECS,
            ),
            allow_failure=True,
        )

        if result.returncode not in {0, 1}:
            raise GitHistoryCheckError(result.stderr.strip())

        findings.extend(parse_git_grep_output(output=result.stdout))

    return tuple(findings)


def collect_git_commits(*, project_root: Path) -> tuple[str, ...]:
    result = run_git(project_root=project_root, args=("rev-list", "--all"))

    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def parse_git_grep_output(*, output: str) -> tuple[GitHistoryFinding, ...]:
    findings: list[GitHistoryFinding] = []

    for raw_line in output.splitlines():
        parsed_line = parse_git_grep_line(raw_line=raw_line)

        if parsed_line is None:
            continue

        commit, path, line_number, line = parsed_line

        if should_skip_line(line=line):
            continue

        findings.extend(
            scan_line_with_specific_rules(
                commit=commit,
                path=path,
                line_number=line_number,
                line=line,
            )
        )
        findings.extend(
            scan_line_for_generic_secret_assignment(
                commit=commit,
                path=path,
                line_number=line_number,
                line=line,
            )
        )

    return tuple(findings)


def parse_git_grep_line(raw_line: str) -> tuple[str, str, int, str] | None:
    first_separator_index = raw_line.find(":")

    if first_separator_index <= 0:
        return None

    commit = raw_line[:first_separator_index]
    rest = raw_line[first_separator_index + 1 :]

    second_separator_index = rest.rfind(":")

    if second_separator_index <= 0:
        return None

    left = rest[:second_separator_index]
    line = rest[second_separator_index + 1 :]

    third_separator_index = left.rfind(":")

    if third_separator_index <= 0:
        return None

    path = normalize_git_path(path=left[:third_separator_index])
    line_number_text = left[third_separator_index + 1 :]

    try:
        line_number = int(line_number_text)
    except ValueError:
        return None

    return commit, path, line_number, line


def scan_line_with_specific_rules(
    *,
    commit: str,
    path: str,
    line_number: int,
    line: str,
) -> tuple[GitHistoryFinding, ...]:
    findings: list[GitHistoryFinding] = []

    for rule in CONTENT_RULES:
        for match in rule.pattern.finditer(line):
            findings.append(
                GitHistoryFinding(
                    commit=commit,
                    path=path,
                    line_number=line_number,
                    rule_id=rule.rule_id,
                    message=rule.message,
                    preview=build_redacted_preview(line=line, span=match.span()),
                )
            )

    return tuple(findings)


def scan_line_for_generic_secret_assignment(
    *,
    commit: str,
    path: str,
    line_number: int,
    line: str,
) -> tuple[GitHistoryFinding, ...]:
    findings: list[GitHistoryFinding] = []

    for match in GENERIC_SECRET_ASSIGNMENT_RE.finditer(line):
        secret_value = match.group("value")

        if should_ignore_generic_secret_assignment(
            path=path,
            operator=match.group("operator"),
            quote=match.group("quote"),
            value=secret_value,
        ):
            continue

        findings.append(
            GitHistoryFinding(
                commit=commit,
                path=path,
                line_number=line_number,
                rule_id="generic-secret-assignment",
                message="В истории Git найдено подозрительное присваивание секрета.",
                preview=build_redacted_preview(line=line, span=match.span("value")),
            )
        )

    return tuple(findings)


def should_ignore_generic_secret_assignment(
    *,
    path: str,
    operator: str,
    quote: str,
    value: str,
) -> bool:
    if is_placeholder_secret_value(value=value):
        return True

    if is_python_type_annotation(path=path, operator=operator):
        return True

    return not quote and is_code_reference_value(value=value)


def should_skip_line(*, line: str) -> bool:
    normalized_line = line.casefold()
    return any(marker in normalized_line for marker in ALLOW_SECRET_LINE_MARKERS)


def is_python_type_annotation(*, path: str, operator: str) -> bool:
    return Path(path).suffix.casefold() == ".py" and operator == ":"


def is_code_reference_value(*, value: str) -> bool:
    normalized_value = value.strip()

    if CODE_REFERENCE_VALUE_RE.fullmatch(normalized_value) is None:
        return False

    return not any(character.isdigit() for character in normalized_value)


def is_placeholder_secret_value(*, value: str) -> bool:
    normalized_value = value.strip().casefold()

    if len(normalized_value) < 12:
        return True

    if len(set(normalized_value)) <= 3:
        return True

    return any(marker in normalized_value for marker in PLACEHOLDER_VALUE_MARKERS)


def matches_any_path_pattern(*, path: str, patterns: tuple[str, ...]) -> bool:
    normalized_path = normalize_git_path(path=path).casefold()
    normalized_name = Path(normalized_path).name.casefold()

    return any(
        fnmatch.fnmatchcase(normalized_path, pattern.casefold())
        or fnmatch.fnmatchcase(normalized_name, pattern.casefold())
        for pattern in patterns
    )


def normalize_git_path(*, path: str) -> str:
    return path.strip().replace("\\", "/")


def build_redacted_preview(*, line: str, span: tuple[int, int]) -> str:
    start, end = span
    preview = f"{line[:start]}<redacted>{line[end:]}".strip()

    if len(preview) <= 160:
        return preview

    return f"{preview[:157]}..."


def deduplicate_findings(
    *,
    findings: Iterable[GitHistoryFinding],
) -> tuple[GitHistoryFinding, ...]:
    unique_findings: dict[tuple[str | None, str, int | None, str, str], GitHistoryFinding] = {}

    for finding in findings:
        key = (
            finding.commit,
            finding.path,
            finding.line_number,
            finding.rule_id,
            finding.preview,
        )
        unique_findings[key] = finding

    return tuple(unique_findings.values())


def format_finding(*, finding: GitHistoryFinding) -> str:
    commit_text = "" if finding.commit is None else f"{finding.commit[:12]}:"
    line_text = "" if finding.line_number is None else f":{finding.line_number}"

    return (
        f"{commit_text}{finding.path}{line_text}: "
        f"{finding.rule_id}: {finding.message} {finding.preview}"
    )


def iter_batches(*, items: tuple[str, ...], batch_size: int) -> Iterable[tuple[str, ...]]:
    for index in range(0, len(items), batch_size):
        yield items[index : index + batch_size]


def run_git(
    *,
    project_root: Path,
    args: tuple[str, ...],
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    completed_process = subprocess.run(
        ("git", *args),
        cwd=project_root,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        text=True,
    )

    if completed_process.returncode != 0 and not allow_failure:
        command = " ".join(("git", *args))
        raise GitHistoryCheckError(f"command failed: {command}\n{completed_process.stderr.strip()}")

    return completed_process


if __name__ == "__main__":
    raise SystemExit(main())
