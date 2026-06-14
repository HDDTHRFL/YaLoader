from __future__ import annotations

from yaloader.infrastructure.ytdlp.metadata_extractor import (
    extract_duration_seconds,
    extract_estimated_file_size_bytes,
)


def test_extract_duration_seconds_from_media_info() -> None:
    assert extract_duration_seconds(media_info={"duration": 125.8}) == 125


def test_extract_estimated_file_size_bytes_prefers_top_level_size() -> None:
    assert extract_estimated_file_size_bytes(media_info={"filesize": 1024}) == 1024


def test_extract_estimated_file_size_bytes_uses_format_size() -> None:
    assert (
        extract_estimated_file_size_bytes(
            media_info={
                "formats": [
                    {"filesize_approx": 1000},
                    {"filesize_approx": 2000},
                ]
            }
        )
        == 2000
    )
