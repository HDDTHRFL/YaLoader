from __future__ import annotations

import pytest

from yaloader.domain.source_identity import build_media_source_key


@pytest.mark.parametrize(
    ("url", "expected_source_key"),
    [
        (
            "https://soundcloud.com/Artist_Name/Track-Name",
            "soundcloud:track:artist_name:track-name",
        ),
        (
            "https://www.soundcloud.com/artist-name/track-name?si=test",
            "soundcloud:track:artist-name:track-name",
        ),
        (
            "https://m.soundcloud.com/artist-name/track-name",
            "soundcloud:track:artist-name:track-name",
        ),
        (
            "https://soundcloud.com/artist-name/sets/playlist-name",
            "soundcloud:playlist:artist-name:playlist-name",
        ),
        (
            "https://soundcloud.com/artist-name",
            "soundcloud:user:artist-name",
        ),
        (
            "https://on.soundcloud.com/AbCdE",
            "soundcloud:short:AbCdE",
        ),
        (
            "https://snd.sc/AbCdE",
            "soundcloud:short:AbCdE",
        ),
        (
            "https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/123",
            "soundcloud:track-id:123",
        ),
        (
            "https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/playlists/456",
            "soundcloud:playlist-id:456",
        ),
        (
            "https://w.soundcloud.com/player/?url=https%3A//soundcloud.com/artist-name/track-name",
            "soundcloud:track:artist-name:track-name",
        ),
    ],
)
def test_build_media_source_key_normalizes_soundcloud_urls(
    *,
    url: str,
    expected_source_key: str,
) -> None:
    assert build_media_source_key(url=url) == expected_source_key


def test_build_media_source_key_returns_original_url_for_unknown_soundcloud_shape() -> None:
    url = "https://w.soundcloud.com/player/?auto_play=false"

    source_key = build_media_source_key(url=url)

    assert source_key == f"soundcloud:url:{url}"
