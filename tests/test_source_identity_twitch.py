from __future__ import annotations

import pytest

from yaloader.domain.source_identity import build_media_source_key


@pytest.mark.parametrize(
    ("url", "expected_source_key"),
    [
        (
            "https://www.twitch.tv/videos/123456789",
            "twitch:video:123456789",
        ),
        (
            "https://m.twitch.tv/videos/123456789?filter=archives&sort=time",
            "twitch:video:123456789",
        ),
        (
            "https://player.twitch.tv/?video=v123456789&parent=localhost",
            "twitch:video:123456789",
        ),
        (
            "https://clips.twitch.tv/ModernClipSlug",
            "twitch:clip:ModernClipSlug",
        ),
        (
            "https://www.twitch.tv/channel/clip/ModernClipSlug",
            "twitch:clip:ModernClipSlug",
        ),
        (
            "https://player.twitch.tv/?clip=ModernClipSlug&parent=localhost",
            "twitch:clip:ModernClipSlug",
        ),
        (
            "https://www.twitch.tv/channel_name",
            "twitch:channel:channel_name",
        ),
    ],
)
def test_build_media_source_key_normalizes_twitch_urls(
    *,
    url: str,
    expected_source_key: str,
) -> None:
    assert build_media_source_key(url=url) == expected_source_key


def test_build_media_source_key_returns_original_url_for_unknown_twitch_shape() -> None:
    url = "https://www.twitch.tv/directory/category/science-technology"

    source_key = build_media_source_key(url=url)

    assert source_key == f"twitch:url:{url}"
