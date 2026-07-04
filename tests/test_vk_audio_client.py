from __future__ import annotations

import base64
from pathlib import Path

import pytest

from yaloader.infrastructure.vk_audio import client as vk_audio_client


def encode_vk_audio_custom_base64(value: str) -> str:
    encoded_value = base64.b64encode(value.encode("latin-1")).decode("ascii")
    translation_table = str.maketrans(
        vk_audio_client.STANDARD_BASE64_ALPHABET,
        vk_audio_client.VK_AUDIO_OBFUSCATION_ALPHABET,
    )

    return encoded_value.translate(translation_table)


def build_encoded_audio_api_unavailable_url(*, direct_url: str, operations: str = "v") -> str:
    encoded_url = encode_vk_audio_custom_base64(direct_url[::-1])
    encoded_operations = encode_vk_audio_custom_base64(operations)

    return f"https://m.vk.com/mp3/audio_api_unavailable.mp3?extra={encoded_url}#{encoded_operations}"


def test_fill_vk_audio_track_user_ids_decodes_audio_api_unavailable_url() -> None:
    direct_url = "https://psv4.userapi.com/audio/file.mp3?token=value"
    encoded_url = build_encoded_audio_api_unavailable_url(direct_url=direct_url)
    track = vk_audio_client.VkAudioTrack(
        owner_id="-2001247452",
        audio_id="41247452",
        direct_url=encoded_url,
    )

    tracks = vk_audio_client.fill_vk_audio_track_user_ids(
        tracks=(track,),
        user_id=87387839,
    )

    assert tracks[0].user_id == 87387839
    assert tracks[0].direct_url == direct_url


def test_adapt_single_page_track_to_requested_audio_id_allows_short_vk_audio_url() -> None:
    requested_audio_id = vk_audio_client.VkAudioId(
        owner_id="87387839",
        audio_id="456239195",
    )
    track = vk_audio_client.VkAudioTrack(
        owner_id="-2001247452",
        audio_id="41247452",
        action_hash="action_hash",
        url_hash="url_hash",
    )

    tracks = vk_audio_client.adapt_single_page_track_to_requested_audio_id(
        audio_id=requested_audio_id,
        page_url="https://m.vk.com/audio87387839_456239195",
        tracks=(track,),
    )

    assert len(tracks) == 1
    assert tracks[0].matches(requested_audio_id)


def test_select_direct_media_from_tracks_decodes_audio_api_unavailable_with_user_id() -> None:
    direct_url = "https://psv4.userapi.com/audio/file.mp3?token=value"
    encoded_url = build_encoded_audio_api_unavailable_url(direct_url=direct_url)
    audio_id = vk_audio_client.VkAudioId(
        owner_id="87387839",
        audio_id="456239195",
    )
    track = vk_audio_client.VkAudioTrack(
        owner_id="-2001247452",
        audio_id="41247452",
        direct_url=encoded_url,
        source_owner_id="87387839",
        source_audio_id="456239195",
        user_id=87387839,
    )

    media = vk_audio_client.select_direct_media_from_tracks(
        audio_id=audio_id,
        tracks=(track,),
    )

    assert media is not None
    assert media.direct_url == direct_url


def test_extract_vk_audio_user_id_from_stats_meta_text() -> None:
    response_text = '{"statsMeta":{"platform":"mvk","id":87387839,"reloadVersion":42}}'

    assert vk_audio_client.extract_vk_audio_user_id(value=None, text=response_text) == 87387839


def test_build_access_keyless_vk_audio_url_removes_access_key() -> None:
    audio_id = vk_audio_client.VkAudioId(
        owner_id="87387839",
        audio_id="456239195",
        access_key="04c0778a82e0210a55",
    )

    url = vk_audio_client.build_access_keyless_vk_audio_url(
        url="https://vk.com/audio87387839_456239195_04c0778a82e0210a55",
        audio_id=audio_id,
    )

    assert url == "https://vk.com/audio87387839_456239195"


def test_build_access_keyless_vk_audio_url_preserves_mobile_host() -> None:
    audio_id = vk_audio_client.VkAudioId(
        owner_id="87387839",
        audio_id="456239195",
        access_key="04c0778a82e0210a55",
    )

    url = vk_audio_client.build_access_keyless_vk_audio_url(
        url="https://m.vk.ru/audio87387839_456239195_04c0778a82e0210a55?from=copy",
        audio_id=audio_id,
    )

    assert url == "https://m.vk.ru/audio87387839_456239195"


def test_resolve_vk_audio_direct_media_prefers_access_keyless_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    expected_media = vk_audio_client.VkAudioDirectMedia(
        audio_id=vk_audio_client.VkAudioId(
            owner_id="87387839",
            audio_id="456239195",
        ),
        direct_url="https://cs9-3v4.vkuseraudio.net/s/v1/ac/example/index.m3u8?token=value",
        title="Expected title",
        artist="Expected artist",
        duration_seconds=120,
    )
    captured_urls: list[str] = []

    def fake_resolve_access_keyless_vk_audio_direct_media(
        *,
        url: str,
        audio_id: vk_audio_client.VkAudioId,
        cookies_file: Path,
        timeout_seconds: float,
    ) -> vk_audio_client.VkAudioDirectMedia | None:
        captured_urls.append(url)

        assert audio_id.value == "87387839_456239195_04c0778a82e0210a55"
        assert cookies_file == tmp_path / "cookies.txt"
        assert timeout_seconds == 20.0

        return expected_media

    def fail_load_vk_audio_cookies(*, cookies_file: Path) -> dict[str, str]:
        raise AssertionError("cookies must not be loaded before the access-keyless fallback succeeds")

    monkeypatch.setattr(
        vk_audio_client,
        "resolve_access_keyless_vk_audio_direct_media",
        fake_resolve_access_keyless_vk_audio_direct_media,
    )
    monkeypatch.setattr(
        vk_audio_client,
        "load_vk_audio_cookies",
        fail_load_vk_audio_cookies,
    )

    media = vk_audio_client.resolve_vk_audio_direct_media(
        url="https://vk.com/audio87387839_456239195_04c0778a82e0210a55",
        cookies_file=tmp_path / "cookies.txt",
    )

    assert captured_urls == ["https://vk.com/audio87387839_456239195_04c0778a82e0210a55"]
    assert media.audio_id.value == "87387839_456239195_04c0778a82e0210a55"
    assert media.direct_url == expected_media.direct_url
    assert media.title == expected_media.title
    assert media.artist == expected_media.artist
    assert media.duration_seconds == expected_media.duration_seconds


def test_build_vk_audio_page_request_headers_uses_plain_html_headers_for_mobile_pages() -> None:
    headers = vk_audio_client.build_vk_audio_page_request_headers(
        url="https://m.vk.com/audio87387839_456239195",
    )

    assert headers["Accept"].startswith("text/html")
    assert headers["Referer"] == "https://m.vk.com/audio"
    assert "Mobile" in headers["User-Agent"]
    assert "Origin" not in headers
    assert "X-Requested-With" not in headers


def test_build_vk_audio_page_request_headers_uses_plain_html_headers_for_desktop_pages() -> None:
    headers = vk_audio_client.build_vk_audio_page_request_headers(
        url="https://vk.com/audio87387839_456239195",
    )

    assert headers["Accept"].startswith("text/html")
    assert headers["Referer"] == "https://vk.com/"
    assert "Windows NT" in headers["User-Agent"]
    assert "Origin" not in headers
    assert "X-Requested-With" not in headers


def test_has_login_required_response_detects_mobile_json_redirect() -> None:
    assert (
        vk_audio_client.has_login_required_response(
            response_dump_parts=(
                (
                    "mobile page",
                    r'{"location":"https:\/\/login.vk.com\/?act=login","version":"1","type":4}',
                ),
            )
        )
        is True
    )


def test_has_login_required_response_detects_desktop_payload_code_3() -> None:
    assert (
        vk_audio_client.has_login_required_response(
            response_dump_parts=(
                (
                    "desktop reload_audio",
                    r'{"payload":["3",["\"hash\""]],"static":"dist\/web\/chunks\/vkcom-kit.js"}',
                ),
            )
        )
        is True
    )
