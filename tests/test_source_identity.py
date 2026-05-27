from __future__ import annotations

import pytest

from yaloader.domain.source_identity import build_media_source_key


@pytest.mark.parametrize(
    ("url", "expected_source_key"),
    [
        (
            "https://www.youtube.com/watch?v=abc123",
            "youtube:video:abc123",
        ),
        (
            "https://www.youtube.com/watch?v=abc123&list=playlist_id&index=10",
            "youtube:video:abc123",
        ),
        (
            "https://youtu.be/abc123?si=test",
            "youtube:video:abc123",
        ),
        (
            "https://www.youtube.com/shorts/abc123?feature=share",
            "youtube:video:abc123",
        ),
        (
            "https://www.youtube.com/embed/abc123",
            "youtube:video:abc123",
        ),
        (
            "https://www.youtube.com/live/abc123",
            "youtube:video:abc123",
        ),
        (
            "https://www.youtube.com/playlist?list=playlist_id",
            "youtube:playlist:playlist_id",
        ),
    ],
)
def test_build_media_source_key_normalizes_youtube_urls(
    *,
    url: str,
    expected_source_key: str,
) -> None:
    assert build_media_source_key(url=url) == expected_source_key


def test_build_media_source_key_strips_outer_spaces() -> None:
    source_key = build_media_source_key(" https://youtu.be/abc123 ")

    assert source_key == "youtube:video:abc123"


def test_build_media_source_key_returns_original_url_for_unknown_youtube_shape() -> None:
    url = "https://www.youtube.com/channel/test"

    source_key = build_media_source_key(url=url)

    assert source_key == f"youtube:url:{url}"


def test_build_media_source_key_rejects_invalid_url() -> None:
    with pytest.raises(ValueError, match="http or https"):
        build_media_source_key(url="not-a-url")
