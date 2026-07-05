from __future__ import annotations

from yaloader.domain.vk_audio_url import (
    VK_AUDIO_PUBLIC_CATALOG_UNSUPPORTED_STATUS_MESSAGE,
    is_unsupported_vk_audio_public_catalog_owner_id,
    is_unsupported_vk_audio_public_catalog_url,
)


def test_vk_audio_public_catalog_url_is_unsupported() -> None:
    assert (
        is_unsupported_vk_audio_public_catalog_url(
            url="https://vk.com/audio-2001247451_41247451_c98d766105ddecb1b3",
        )
        is True
    )


def test_regular_vk_audio_track_url_is_supported() -> None:
    assert is_unsupported_vk_audio_public_catalog_url(url="https://vk.com/audio87387839_456239195") is False


def test_non_vk_url_is_not_treated_as_public_catalog_audio() -> None:
    assert is_unsupported_vk_audio_public_catalog_url(url="https://www.youtube.com/watch?v=test") is False


def test_public_catalog_owner_id_detection() -> None:
    assert is_unsupported_vk_audio_public_catalog_owner_id(owner_id="-2001247451") is True
    assert is_unsupported_vk_audio_public_catalog_owner_id(owner_id="87387839") is False


def test_public_catalog_status_message_is_user_facing() -> None:
    assert "публичного каталога" in VK_AUDIO_PUBLIC_CATALOG_UNSUPPORTED_STATUS_MESSAGE
    assert "обычную ссылку" in VK_AUDIO_PUBLIC_CATALOG_UNSUPPORTED_STATUS_MESSAGE
