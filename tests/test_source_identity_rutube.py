from __future__ import annotations

from yaloader.domain.source_identity import build_media_source_key


def test_build_media_source_key_for_rutube_video() -> None:
    assert build_media_source_key(url="https://rutube.ru/video/1234567890abcdef/") == "rutube:video:1234567890abcdef"


def test_build_media_source_key_for_rutube_embed() -> None:
    assert (
        build_media_source_key(url="https://rutube.ru/play/embed/1234567890abcdef") == "rutube:video:1234567890abcdef"
    )
