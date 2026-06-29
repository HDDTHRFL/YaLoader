from __future__ import annotations

import re
from pathlib import Path
from typing import Final

MAX_OUTPUT_FILE_STEM_LENGTH: Final = 200
DEFAULT_OUTPUT_FILE_STEM: Final = "download"

WINDOWS_RESERVED_FILENAME_CHARS_RE: Final = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
TRAILING_GENERATED_ID_SUFFIX_RE: Final = re.compile(r"\s+\[[A-Za-z0-9_-]{11}\]\s*$")
WHITESPACE_RE: Final = re.compile(r"\s+")


def build_unique_output_template(
    *,
    target_dir: Path,
    title: str,
    output_extension: str,
) -> str:
    normalized_stem = normalize_output_file_stem(title=title)
    unique_stem = build_unique_output_file_stem(
        target_dir=target_dir,
        stem=normalized_stem,
        output_extension=output_extension,
    )

    return str(target_dir / f"{unique_stem}.%(ext)s")


def normalize_output_file_stem(*, title: str) -> str:
    title_without_generated_id = TRAILING_GENERATED_ID_SUFFIX_RE.sub("", title)
    sanitized_title = WINDOWS_RESERVED_FILENAME_CHARS_RE.sub(
        " ",
        title_without_generated_id,
    )
    normalized_title = WHITESPACE_RE.sub(" ", sanitized_title).strip(" .")

    if not normalized_title:
        normalized_title = DEFAULT_OUTPUT_FILE_STEM

    return trim_output_file_stem(stem=normalized_title)


def build_unique_output_file_stem(
    *,
    target_dir: Path,
    stem: str,
    output_extension: str,
) -> str:
    existing_file_names = collect_existing_file_names(target_dir=target_dir)
    normalized_extension = output_extension.strip().lstrip(".")
    base_stem = trim_output_file_stem(stem=stem)

    if not does_output_file_exist(
        existing_file_names=existing_file_names,
        stem=base_stem,
        output_extension=normalized_extension,
    ):
        return base_stem

    duplicate_index = 1

    while True:
        suffix = f" ({duplicate_index})"
        candidate_stem = (
            trim_output_file_stem(
                stem=base_stem,
                max_length=MAX_OUTPUT_FILE_STEM_LENGTH - len(suffix),
            )
            + suffix
        )

        if not does_output_file_exist(
            existing_file_names=existing_file_names,
            stem=candidate_stem,
            output_extension=normalized_extension,
        ):
            return candidate_stem

        duplicate_index += 1


def collect_existing_file_names(*, target_dir: Path) -> frozenset[str]:
    if not target_dir.is_dir():
        return frozenset()

    return frozenset(file_path.name.casefold() for file_path in target_dir.iterdir() if file_path.is_file())


def does_output_file_exist(
    *,
    existing_file_names: frozenset[str],
    stem: str,
    output_extension: str,
) -> bool:
    return f"{stem}.{output_extension}".casefold() in existing_file_names


def trim_output_file_stem(
    *,
    stem: str,
    max_length: int = MAX_OUTPUT_FILE_STEM_LENGTH,
) -> str:
    trimmed_stem = stem[: max(1, max_length)].strip(" .")

    if trimmed_stem:
        return trimmed_stem

    return DEFAULT_OUTPUT_FILE_STEM
