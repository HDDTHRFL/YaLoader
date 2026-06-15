from __future__ import annotations

import pytest

from yaloader.domain.source_identity import build_media_source_key


@pytest.mark.parametrize(
    ("url", "expected_source_key"),
    [
        (
            "https://vkvideo.ru/video-123456789_456239017",
            "vkvideo:video:-123456789_456239017",
        ),
        (
            "https://www.vkvideo.ru/video-123456789_456239017?list=test",
            "vkvideo:video:-123456789_456239017",
        ),
        (
            "https://vk.com/video-123456789_456239017",
            "vkvideo:video:-123456789_456239017",
        ),
        (
            "https://m.vk.com/video-123456789_456239017",
            "vkvideo:video:-123456789_456239017",
        ),
        (
            "https://vk.com/video_ext.php?oid=-123456789&id=456239017&hash=test",
            "vkvideo:video:-123456789_456239017",
        ),
        (
            "https://vk.com/video?z=video-123456789_456239017%2Fclub123",
            "vkvideo:video:-123456789_456239017",
        ),
        (
            "https://vk.com/clip-123456789_456239017",
            "vkvideo:video:-123456789_456239017",
        ),
    ],
)
def test_build_media_source_key_normalizes_vk_video_urls(
    *,
    url: str,
    expected_source_key: str,
) -> None:
    assert build_media_source_key(url=url) == expected_source_key


def test_build_media_source_key_returns_original_url_for_unknown_vk_video_shape() -> None:
    url = "https://vk.com/some-page"

    source_key = build_media_source_key(url=url)

    assert source_key == f"vkvideo:url:{url}"
