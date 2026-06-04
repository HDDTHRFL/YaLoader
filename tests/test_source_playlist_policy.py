from __future__ import annotations

import pytest

from yaloader.domain.source_playlist_policy import should_include_playlist_for_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/playlist?list=PL123",
        "https://youtube.com/playlist?list=PL123",
        "https://m.youtube.com/playlist?list=PL123",
        "https://music.youtube.com/playlist?list=PL123",
        "https://www.youtube.com/playlist/?list=PL123",
    ],
)
def test_should_include_playlist_for_playlist_page(url: str) -> None:
    assert should_include_playlist_for_url(url=url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=video123&list=PL123",
        "https://www.youtube.com/shorts/video123?list=PL123",
        "https://youtu.be/video123?list=PL123",
        "https://www.youtube.com/playlist",
        "https://www.youtube.com/playlist?list=",
        "https://example.com/playlist?list=PL123",
    ],
)
def test_should_not_include_playlist_for_single_video_or_invalid_playlist(url: str) -> None:
    assert should_include_playlist_for_url(url=url) is False
