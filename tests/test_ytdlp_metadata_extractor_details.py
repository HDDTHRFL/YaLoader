from __future__ import annotations

from yaloader.infrastructure.ytdlp.metadata_extractor import (
    extract_duration_seconds,
    extract_estimated_file_size_bytes,
    extract_file_size_metadata,
)


def test_extract_duration_seconds_from_media_info() -> None:
    assert extract_duration_seconds(media_info={"duration": 125.8}) == 125


def test_extract_file_size_metadata_prefers_selected_formats() -> None:
    result = extract_file_size_metadata(
        media_info={
            "filesize_approx": 10_000,
            "requested_formats": [
                {"filesize": 1000},
                {"filesize": 2000},
            ],
        }
    )

    assert result.size_bytes == 3000
    assert result.is_estimated is False


def test_extract_file_size_metadata_uses_top_level_size_as_exact() -> None:
    result = extract_file_size_metadata(media_info={"filesize": 1024})

    assert result.size_bytes == 1024
    assert result.is_estimated is False


def test_extract_file_size_metadata_marks_bitrate_calculation_as_estimated() -> None:
    result = extract_file_size_metadata(
        media_info={
            "duration": 100,
            "tbr": 800,
        }
    )

    assert result.size_bytes == 10_000_000
    assert result.is_estimated is True


def test_extract_file_size_metadata_uses_selected_format_bitrate() -> None:
    result = extract_file_size_metadata(
        media_info={
            "duration": 100,
            "requested_formats": [
                {
                    "duration": 60,
                    "tbr": 1000,
                },
                {
                    "duration": 60,
                    "vbr": 800,
                    "abr": 128,
                },
            ],
        }
    )

    assert result.size_bytes == 14_460_000
    assert result.is_estimated is True


def test_extract_file_size_metadata_does_not_use_all_available_formats() -> None:
    result = extract_file_size_metadata(
        media_info={
            "formats": [
                {"filesize_approx": 1_000_000},
                {"filesize_approx": 2_000_000},
            ]
        }
    )

    assert result.size_bytes is None
    assert result.is_estimated is False


def test_extract_estimated_file_size_bytes_keeps_backward_compatible_api() -> None:
    assert extract_estimated_file_size_bytes(media_info={"filesize": 1024}) == 1024
