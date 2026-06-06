from __future__ import annotations

from pathlib import Path

from yaloader.infrastructure.ytdlp.output_naming import (
    MAX_OUTPUT_FILE_STEM_LENGTH,
    build_unique_output_file_stem,
    build_unique_output_template,
    normalize_output_file_stem,
)


def test_normalize_output_file_stem_removes_trailing_youtube_generated_id() -> None:
    normalized_stem = normalize_output_file_stem(
        title="Audio & Merika - Test Track [dQw4w9WgXcQ]",
    )

    assert normalized_stem == "Audio & Merika - Test Track"


def test_normalize_output_file_stem_keeps_non_generated_bracket_text() -> None:
    normalized_stem = normalize_output_file_stem(
        title="Audio & Merika [official video]",
    )

    assert normalized_stem == "Audio & Merika [official video]"


def test_normalize_output_file_stem_replaces_windows_reserved_characters() -> None:
    normalized_stem = normalize_output_file_stem(
        title='Video <Name>: "Part 1" / Test? * [dQw4w9WgXcQ]',
    )

    assert normalized_stem == "Video Name Part 1 Test"


def test_normalize_output_file_stem_returns_default_for_empty_sanitized_title() -> None:
    normalized_stem = normalize_output_file_stem(
        title='<>:"/\\|?*',
    )

    assert normalized_stem == "download"


def test_build_unique_output_file_stem_returns_base_stem_when_file_does_not_exist(
    tmp_path: Path,
) -> None:
    unique_stem = build_unique_output_file_stem(
        target_dir=tmp_path,
        stem="Video",
        output_extension="mp4",
    )

    assert unique_stem == "Video"


def test_build_unique_output_file_stem_adds_windows_style_duplicate_suffix(
    tmp_path: Path,
) -> None:
    (tmp_path / "Video.mp4").write_text("first", encoding="utf-8")
    (tmp_path / "Video (1).mp4").write_text("second", encoding="utf-8")

    unique_stem = build_unique_output_file_stem(
        target_dir=tmp_path,
        stem="Video",
        output_extension="mp4",
    )

    assert unique_stem == "Video (2)"


def test_build_unique_output_file_stem_compares_existing_names_case_insensitively(
    tmp_path: Path,
) -> None:
    (tmp_path / "Video.MP4").write_text("first", encoding="utf-8")

    unique_stem = build_unique_output_file_stem(
        target_dir=tmp_path,
        stem="video",
        output_extension="mp4",
    )

    assert unique_stem == "video (1)"


def test_build_unique_output_file_stem_ignores_different_extensions(
    tmp_path: Path,
) -> None:
    (tmp_path / "Video.webm").write_text("first", encoding="utf-8")

    unique_stem = build_unique_output_file_stem(
        target_dir=tmp_path,
        stem="Video",
        output_extension="mp4",
    )

    assert unique_stem == "Video"


def test_build_unique_output_file_stem_keeps_max_length_with_duplicate_suffix(
    tmp_path: Path,
) -> None:
    long_stem = "A" * MAX_OUTPUT_FILE_STEM_LENGTH
    (tmp_path / f"{long_stem}.mp4").write_text("first", encoding="utf-8")

    unique_stem = build_unique_output_file_stem(
        target_dir=tmp_path,
        stem=long_stem,
        output_extension="mp4",
    )

    assert unique_stem.endswith(" (1)")
    assert len(unique_stem) == MAX_OUTPUT_FILE_STEM_LENGTH


def test_build_unique_output_template_uses_normalized_unique_stem(tmp_path: Path) -> None:
    (tmp_path / "Video.mp4").write_text("first", encoding="utf-8")

    output_template = build_unique_output_template(
        target_dir=tmp_path,
        title="Video [dQw4w9WgXcQ]",
        output_extension="mp4",
    )

    assert output_template == str(tmp_path / "Video (1).%(ext)s")
