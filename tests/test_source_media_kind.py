from __future__ import annotations

import pytest

from yaloader.domain.source_media_kind import (
    SourceMediaKind,
    detect_source_media_kind,
    is_youtube_shorts_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/shorts/abc123",
        "https://youtube.com/shorts/abc123?feature=share",
        "https://m.youtube.com/shorts/abc123",
    ],
)
def test_is_youtube_shorts_url_for_shorts(url: str) -> None:
    assert is_youtube_shorts_url(url=url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abc123",
        "https://youtu.be/abc123",
        "https://example.com/shorts/abc123",
    ],
)
def test_is_youtube_shorts_url_for_non_shorts(url: str) -> None:
    assert is_youtube_shorts_url(url=url) is False


def test_detect_source_media_kind_prefers_playlist_flag() -> None:
    assert (
        detect_source_media_kind(
            url="https://www.youtube.com/shorts/abc123",
            include_playlist=True,
        )
        is SourceMediaKind.PLAYLIST
    )


def test_detect_source_media_kind_detects_shorts() -> None:
    assert (
        detect_source_media_kind(
            url="https://www.youtube.com/shorts/abc123",
            include_playlist=False,
        )
        is SourceMediaKind.SHORTS
    )


def test_detect_source_media_kind_defaults_to_video() -> None:
    assert (
        detect_source_media_kind(
            url="https://www.youtube.com/watch?v=abc123",
            include_playlist=False,
        )
        is SourceMediaKind.VIDEO
    )
