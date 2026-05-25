from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


@dataclass(frozen=True)
class BundleConfig:
    project_name: str = "YaLoader"
    output_dir_name: str = "_bundle"
    text_bundle_name: str = "project_yaloader_bundle.txt"
    zip_bundle_name: str = "project_yaloader_bundle.zip"
    base64_bundle_name: str = "project_yaloader_bundle_b64.txt"
    base64_line_length: int = 76
    excluded_dir_names: frozenset[str] = frozenset(
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
    excluded_file_names: frozenset[str] = frozenset(
        {
            "uv.lock",
        }
    )
    included_file_names: frozenset[str] = frozenset(
        {
            ".gitattributes",
            ".gitignore",
            ".python-version",
        }
    )
    included_suffixes: frozenset[str] = frozenset(
        {
            ".bat",
            ".cfg",
            ".css",
            ".html",
            ".ini",
            ".json",
            ".md",
            ".ps1",
            ".py",
            ".qrc",
            ".qss",
            ".toml",
            ".txt",
            ".ui",
            ".yaml",
            ".yml",
        }
    )


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config = BundleConfig()

    output_dir = project_root / config.output_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)

    files = collect_project_files(project_root=project_root, config=config)

    text_bundle_path = output_dir / config.text_bundle_name
    zip_bundle_path = output_dir / config.zip_bundle_name
    base64_bundle_path = output_dir / config.base64_bundle_name

    create_text_bundle(
        project_root=project_root,
        files=files,
        output_path=text_bundle_path,
        config=config,
    )
    create_zip_bundle(
        project_root=project_root,
        files=files,
        output_path=zip_bundle_path,
        config=config,
    )
    create_base64_bundle(
        zip_bundle_path=zip_bundle_path,
        output_path=base64_bundle_path,
        line_length=config.base64_line_length,
    )

    print("Bundle created successfully.")
    print(f"Text bundle:   {text_bundle_path}")
    print(f"ZIP bundle:    {zip_bundle_path}")
    print(f"Base64 bundle: {base64_bundle_path}")
    print(f"Files included: {len(files)}")


def collect_project_files(project_root: Path, config: BundleConfig) -> list[Path]:
    files: list[Path] = []

    for file_path in project_root.rglob("*"):
        if not file_path.is_file():
            continue

        if should_include_file(
            project_root=project_root,
            file_path=file_path,
            config=config,
        ):
            files.append(file_path)

    return sorted(files, key=lambda path: path.relative_to(project_root).as_posix().casefold())


def should_include_file(project_root: Path, file_path: Path, config: BundleConfig) -> bool:
    relative_path = file_path.relative_to(project_root)

    if has_excluded_directory(relative_path=relative_path, config=config):
        return False

    if file_path.name in config.excluded_file_names:
        return False

    if file_path.name in config.included_file_names:
        return True

    return file_path.suffix.lower() in config.included_suffixes


def has_excluded_directory(relative_path: Path, config: BundleConfig) -> bool:
    return any(path_part in config.excluded_dir_names for path_part in relative_path.parts)


def create_text_bundle(
    project_root: Path,
    files: list[Path],
    output_path: Path,
    config: BundleConfig,
) -> None:
    created_at = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines: list[str] = [
        f"# {config.project_name} project bundle",
        f"# Created: {created_at}",
        f"# Files included: {len(files)}",
        "",
    ]

    for file_path in files:
        relative_path = file_path.relative_to(project_root).as_posix()
        lines.append(f"===== FILE: {relative_path} =====")
        lines.append(read_text_file(file_path))
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def read_text_file(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        return f"[UNREADABLE UTF-8 TEXT FILE: {error}]"


def create_zip_bundle(
    project_root: Path,
    files: list[Path],
    output_path: Path,
    config: BundleConfig,
) -> None:
    created_at = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    manifest = "\n".join(
        [
            f"Project: {config.project_name}",
            f"Created: {created_at}",
            f"Files included: {len(files)}",
            "",
        ]
    )

    with ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as zip_file:
        zip_file.writestr("BUNDLE_MANIFEST.txt", manifest)

        for file_path in files:
            archive_name = file_path.relative_to(project_root).as_posix()
            zip_file.write(filename=file_path, arcname=archive_name)


def create_base64_bundle(zip_bundle_path: Path, output_path: Path, line_length: int) -> None:
    encoded_text = base64.b64encode(zip_bundle_path.read_bytes()).decode("ascii")
    wrapped_text = wrap_text(text=encoded_text, line_length=line_length)
    output_path.write_text(wrapped_text, encoding="utf-8", newline="\n")


def wrap_text(text: str, line_length: int) -> str:
    return "\n".join(
        text[index : index + line_length] for index in range(0, len(text), line_length)
    )


if __name__ == "__main__":
    main()
