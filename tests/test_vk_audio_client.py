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


def test_select_direct_media_from_tracks_accepts_public_negative_vk_audio_url() -> None:
    direct_url = "https://psv4.userapi.com/audio/file.mp3?token=value"
    audio_id = vk_audio_client.parse_vk_audio_id(url="https://vk.com/audio-2001247451_41247451")
    track = vk_audio_client.VkAudioTrack(
        owner_id="-2001247451",
        audio_id="41247451",
        direct_url=direct_url,
        title="Track title",
        artist="Artist",
        duration_seconds=123,
    )

    media = vk_audio_client.select_direct_media_from_tracks(
        audio_id=audio_id,
        tracks=(track,),
    )

    assert media is not None
    assert media.audio_id == audio_id
    assert media.direct_url == direct_url
    assert media.title == "Track title"
    assert media.artist == "Artist"
    assert media.duration_seconds == 123


def test_parse_vk_audio_id_keeps_public_negative_access_key_from_vk_url() -> None:
    audio_id = vk_audio_client.parse_vk_audio_id(
        url="https://vk.com/audio-2001247451_41247451_c98d766105ddecb1b3",
    )

    assert audio_id.owner_id == "-2001247451"
    assert audio_id.audio_id == "41247451"
    assert audio_id.access_key == "c98d766105ddecb1b3"
    assert audio_id.value == "-2001247451_41247451_c98d766105ddecb1b3"
    assert audio_id.base_value == "-2001247451_41247451"
    assert audio_id.display_value == "-2001247451_41247451_<access-key>"
    assert audio_id.safe_file_stem == "vk_audio_-2001247451_41247451"


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


def test_has_login_required_response_ignores_desktop_bad_hash_payload_code_3() -> None:
    assert (
        vk_audio_client.has_login_required_response(
            response_dump_parts=(
                (
                    "desktop reload_audio",
                    r'{"payload":["3",["\"hash\""]],"static":"dist\/web\/chunks\/vkcom-kit.js"}',
                ),
            )
        )
        is False
    )


def test_parse_netscape_cookie_line_accepts_httponly_vk_cookie() -> None:
    cookie = vk_audio_client.parse_netscape_cookie_line(
        line="#HttpOnly_.vk.com\tTRUE\t/\tTRUE\t1893456000\tremixsid\tvalue123",
    )

    assert cookie == ("remixsid", "value123")


def test_load_vk_audio_cookies_keeps_httponly_vk_cookie(tmp_path: Path) -> None:
    cookies_file = tmp_path / "cookies.txt"
    cookies_file.write_text(
        "# Netscape HTTP Cookie File\n#HttpOnly_.vk.com\tTRUE\t/\tTRUE\t1893456000\tremixsid\tvalue123\n",
        encoding="utf-8",
    )

    cookies = vk_audio_client.load_vk_audio_cookies(cookies_file=cookies_file)

    assert cookies["remixsid"] == "value123"
    assert cookies["remixaudio_show_alert_today"] == "0"
    assert cookies["remixmdevice"] == "1920/1080/2/!!-!!!!"


def test_load_vk_audio_cookies_preserves_domain_specific_duplicate_cookie_names(tmp_path: Path) -> None:
    cookies_file = tmp_path / "cookies.txt"
    cookies_file.write_text(
        "# Netscape HTTP Cookie File\n"
        "#HttpOnly_.vk.com\tTRUE\t/\tTRUE\t1893456000\tremixsid\tvk_value\n"
        "#HttpOnly_.vk.ru\tTRUE\t/\tTRUE\t1893456000\tremixsid\tru_value\n",
        encoding="utf-8",
    )

    cookies = vk_audio_client.load_vk_audio_cookies(cookies_file=cookies_file)

    vk_request = vk_audio_client.httpx.Request("GET", "https://m.vk.com/audio")
    cookies.set_cookie_header(vk_request)

    vk_ru_request = vk_audio_client.httpx.Request("GET", "https://m.vk.ru/audio")
    cookies.set_cookie_header(vk_ru_request)

    assert "remixsid=vk_value" in vk_request.headers["cookie"]
    assert "remixsid=ru_value" not in vk_request.headers["cookie"]
    assert "remixsid=ru_value" in vk_ru_request.headers["cookie"]


def test_resolve_from_desktop_reload_audio_decodes_audio_api_unavailable_track(monkeypatch: pytest.MonkeyPatch) -> None:
    direct_url = "https://psv4.userapi.com/audio/file.mp3?token=value"
    encoded_url = build_encoded_audio_api_unavailable_url(direct_url=direct_url)
    audio_id = vk_audio_client.VkAudioId(owner_id="-2001247451", audio_id="41247451")
    track = [
        "41247451",
        "-2001247451",
        encoded_url,
        "Track title",
        "Artist",
        123,
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "a/b/action/c/d/url",
        "",
        {"vk_id": 12345},
    ]

    def fake_request_vk_desktop_audio_reload(
        *,
        audio_id: vk_audio_client.VkAudioId,
        cookies: vk_audio_client.httpx.Cookies,
        timeout_seconds: float,
    ) -> str:
        return vk_audio_client.json.dumps([track])

    monkeypatch.setattr(
        vk_audio_client,
        "request_vk_desktop_audio_reload",
        fake_request_vk_desktop_audio_reload,
    )

    response_dump_parts: list[tuple[str, str]] = []
    media = vk_audio_client.resolve_from_desktop_reload_audio(
        audio_id=audio_id,
        cookies=vk_audio_client.httpx.Cookies(),
        timeout_seconds=20.0,
        response_dump_parts=response_dump_parts,
    )

    assert media is not None
    assert media.direct_url == direct_url
    assert media.title == "Track title"
    assert media.artist == "Artist"
    assert media.duration_seconds == 123


def test_has_login_required_response_ignores_plain_html_login_link() -> None:
    assert (
        vk_audio_client.has_login_required_response(
            response_dump_parts=(("html", '<a href="https://login.vk.com/">login</a>'),),
        )
        is False
    )


def test_collect_desktop_hash_reload_audio_ids_from_bad_hash_payload() -> None:
    audio_id = vk_audio_client.VkAudioId(owner_id="-2001089318", audio_id="149089318")
    payload = {
        "payload": [
            "3",
            [
                '\\"60f494e83cd32d7ef5\\"',
                '\\"Lz8-\\"',
                '\\"eUxZPn4al817LBvSqQ0XmweKhxjIFLce6NB3iqSF_Is\\"',
            ],
        ],
    }

    candidates = vk_audio_client.collect_desktop_hash_reload_audio_ids(
        audio_id=audio_id,
        payload=payload,
    )

    assert "-2001089318_149089318_60f494e83cd32d7ef5_Lz8-" in candidates
    assert "-2001089318_149089318_60f494e83cd32d7ef5_eUxZPn4al817LBvSqQ0XmweKhxjIFLce6NB3iqSF_Is" in candidates
    assert len(candidates) <= vk_audio_client.MAX_DESKTOP_HASH_RELOAD_ATTEMPTS


def test_payload_code_three_without_login_location_is_not_login_required() -> None:
    payload = {
        "payload": [
            "3",
            [
                '\\"60f494e83cd32d7ef5\\"',
                '\\"Lz8-\\"',
                '\\"eUxZPn4al817LBvSqQ0XmweKhxjIFLce6NB3iqSF_Is\\"',
            ],
        ],
    }

    assert vk_audio_client.is_login_required_payload(value=payload) is False


def test_build_mobile_load_section_request_data_keeps_playlist_access_hash() -> None:
    data = vk_audio_client.build_mobile_load_section_request_data(
        owner_id="-2001247451",
        playlist_id="41247451",
        access_hash="c98d766105ddecb1b3",
    )

    assert data["act"] == "load_section"
    assert data["owner_id"] == "-2001247451"
    assert data["playlist_id"] == "41247451"
    assert data["access_hash"] == "c98d766105ddecb1b3"


def test_is_probable_vk_audio_playlist_id_detects_negative_public_playlist_id() -> None:
    assert (
        vk_audio_client.is_probable_vk_audio_playlist_id(
            audio_id=vk_audio_client.VkAudioId(owner_id="-2001247451", audio_id="41247451"),
        )
        is True
    )


def test_select_first_direct_media_from_playlist_tracks_returns_first_downloadable_track() -> None:
    playlist_audio_id = vk_audio_client.VkAudioId(
        owner_id="-2001247451",
        audio_id="41247451",
        access_key="c98d766105ddecb1b3",
    )
    track = vk_audio_client.VkAudioTrack(
        owner_id="87387839",
        audio_id="456239195",
        title="Track title",
        artist="Artist",
        duration_seconds=123,
        direct_url="https://psv4.userapi.com/audio/file.mp3?token=value",
    )

    media = vk_audio_client.select_first_direct_media_from_playlist_tracks(
        playlist_audio_id=playlist_audio_id,
        tracks=(track,),
    )

    assert media is not None
    assert media.audio_id == playlist_audio_id
    assert media.direct_url == "https://psv4.userapi.com/audio/file.mp3?token=value"
    assert media.title == "Track title"
    assert media.artist == "Artist"
    assert media.duration_seconds == 123


def test_decode_public_catalog_audio_owner_id_from_negative_200_prefix() -> None:
    assert vk_audio_client.decode_public_catalog_audio_owner_id(owner_id="-2001247451") == "1247451"


def test_build_vk_audio_equivalent_ids_keeps_original_and_decoded_public_catalog_id() -> None:
    audio_id = vk_audio_client.VkAudioId(
        owner_id="-2001247451",
        audio_id="41247451",
        access_key="c98d766105ddecb1b3",
    )

    equivalent_audio_ids = vk_audio_client.build_vk_audio_equivalent_ids(audio_id=audio_id)

    assert equivalent_audio_ids == (
        vk_audio_client.VkAudioId(
            owner_id="-2001247451",
            audio_id="41247451",
            access_key="c98d766105ddecb1b3",
        ),
        vk_audio_client.VkAudioId(
            owner_id="1247451",
            audio_id="41247451",
            access_key="c98d766105ddecb1b3",
        ),
    )


def test_vk_audio_track_matches_decoded_public_catalog_id() -> None:
    audio_id = vk_audio_client.VkAudioId(
        owner_id="-2001247451",
        audio_id="41247451",
        access_key="c98d766105ddecb1b3",
    )
    track = vk_audio_client.VkAudioTrack(
        owner_id="1247451",
        audio_id="41247451",
        direct_url="https://psv4.userapi.com/audio/file.mp3?token=value",
    )

    assert track.matches(audio_id) is True


def test_build_initial_mobile_audio_id_candidates_includes_decoded_public_catalog_id() -> None:
    audio_id = vk_audio_client.VkAudioId(
        owner_id="-2001247451",
        audio_id="41247451",
        access_key="c98d766105ddecb1b3",
    )

    candidates = vk_audio_client.build_initial_mobile_audio_id_candidates(audio_id=audio_id)

    assert candidates == (
        "-2001247451_41247451",
        "-2001247451_41247451_c98d766105ddecb1b3",
        "1247451_41247451",
        "1247451_41247451_c98d766105ddecb1b3",
    )


def test_unsupported_public_catalog_vk_audio_link_is_rejected_before_network() -> None:
    audio_id = vk_audio_client.VkAudioId(
        owner_id="-2001247451",
        audio_id="41247451",
        access_key="c98d766105ddecb1b3",
    )

    with pytest.raises(
        vk_audio_client.VkAudioUnsupportedPublicCatalogLinkError,
        match="публичного каталога",
    ):
        vk_audio_client.ensure_vk_audio_link_is_supported(audio_id=audio_id)


def test_regular_vk_audio_link_is_still_supported_by_guard() -> None:
    audio_id = vk_audio_client.VkAudioId(
        owner_id="87387839",
        audio_id="456239195",
    )

    vk_audio_client.ensure_vk_audio_link_is_supported(audio_id=audio_id)
