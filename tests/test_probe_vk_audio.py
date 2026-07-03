from __future__ import annotations

import base64
import html as html_tools
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def load_probe_vk_audio_module() -> ModuleType:
    project_root = Path(__file__).resolve().parents[1]
    module_path = project_root / "scripts" / "probe_vk_audio.py"
    module_name = "probe_vk_audio_script"
    module_spec = importlib.util.spec_from_file_location(
        module_name,
        module_path,
    )

    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Could not load probe_vk_audio.py: {module_path}")

    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)

    return module


probe_vk_audio = load_probe_vk_audio_module()


def encode_vk_audio_custom_base64(value: str) -> str:
    encoded_value = base64.b64encode(value.encode("latin-1")).decode("ascii")
    translation_table = str.maketrans(
        probe_vk_audio.STANDARD_BASE64_ALPHABET,
        probe_vk_audio.VK_AUDIO_OBFUSCATION_ALPHABET,
    )

    return encoded_value.translate(translation_table)


def build_encoded_audio_api_unavailable_url(*, direct_url: str, operations: str = "v") -> str:
    encoded_url = encode_vk_audio_custom_base64(direct_url[::-1])
    encoded_operations = encode_vk_audio_custom_base64(operations)

    return f"https://m.vk.com/mp3/audio_api_unavailable.mp3?extra={encoded_url}#{encoded_operations}"


def test_parse_vk_audio_id_from_vk_url() -> None:
    audio_id = probe_vk_audio.parse_vk_audio_id(url="https://vk.com/audio-2001247452_41247452")

    assert audio_id.owner_id == "-2001247452"
    assert audio_id.audio_id == "41247452"
    assert audio_id.access_key is None
    assert audio_id.value == "-2001247452_41247452"
    assert audio_id.base_value == "-2001247452_41247452"
    assert audio_id.display_value == "-2001247452_41247452"
    assert audio_id.safe_file_stem == "vk_audio_-2001247452_41247452"


def test_parse_vk_audio_id_keeps_access_key_from_vk_url() -> None:
    audio_id = probe_vk_audio.parse_vk_audio_id(
        url="https://vk.com/audio133993362_456242612_cb6b8410a741a6993a",
    )

    assert audio_id.owner_id == "133993362"
    assert audio_id.audio_id == "456242612"
    assert audio_id.access_key == "cb6b8410a741a6993a"
    assert audio_id.value == "133993362_456242612_cb6b8410a741a6993a"
    assert audio_id.base_value == "133993362_456242612"
    assert audio_id.display_value == "133993362_456242612_<access-key>"
    assert audio_id.safe_file_stem == "vk_audio_133993362_456242612"


def test_parse_vk_audio_id_rejects_video_url() -> None:
    try:
        probe_vk_audio.parse_vk_audio_id(url="https://vk.com/video-123_456")
    except probe_vk_audio.VkAudioProbeError as error:
        assert "VK Audio" in str(error)
    else:
        raise AssertionError("VK video URL must not be accepted as VK Audio")


def test_parse_netscape_cookie_line() -> None:
    cookie = probe_vk_audio.parse_netscape_cookie_line(
        line=".vk.com\tTRUE\t/\tTRUE\t1893456000\tremixsid\tvalue123",
    )

    assert cookie == ("remixsid", "value123")


def test_load_vk_audio_cookies_adds_default_audio_cookies(tmp_path: Path) -> None:
    cookies_file = tmp_path / "cookies.txt"
    cookies_file.write_text(
        "# Netscape HTTP Cookie File\n.vk.com\tTRUE\t/\tTRUE\t1893456000\tremixsid\tvalue123\n",
        encoding="utf-8",
    )

    cookies = probe_vk_audio.load_vk_audio_cookies(cookies_file=cookies_file)

    assert cookies["remixsid"] == "value123"
    assert cookies["remixaudio_show_alert_today"] == "0"
    assert cookies["remixmdevice"] == "1920/1080/2/!!-!!!!"


def test_parse_vk_al_json_payload_with_html_comment_prefix() -> None:
    payload = probe_vk_audio.parse_vk_al_json_payload(
        text='<!--{"payload":[["https:\\/\\/example.com\\/audio.mp3?x=1"]]}',
    )

    assert isinstance(payload, dict)
    assert probe_vk_audio.find_direct_audio_url(value=payload) == "https://example.com/audio.mp3?x=1"


def test_extract_audio_tracks_from_html_parses_list_data_audio() -> None:
    audio_data = [
        456242612,
        133993362,
        "https://psv4.userapi.com/audio/file.mp3?token=value",
        "<b>Track title</b>",
        "Artist",
        123,
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "x/y/action_hash/a/b/url_hash",
        "",
    ]
    escaped_audio_data = html_tools.escape(json.dumps(audio_data), quote=True)
    html = f'<div id="au_search_items"><div class="audio_item" data-audio="{escaped_audio_data}"></div></div>'

    tracks = probe_vk_audio.extract_audio_tracks_from_html(html_text=html)

    assert len(tracks) == 1
    assert tracks[0].owner_id == "133993362"
    assert tracks[0].audio_id == "456242612"
    assert tracks[0].direct_url == "https://psv4.userapi.com/audio/file.mp3?token=value"
    assert tracks[0].title == "Track title"
    assert tracks[0].artist == "Artist"
    assert tracks[0].duration_seconds == 123
    assert tracks[0].action_hash == "action_hash"
    assert tracks[0].url_hash == "url_hash"
    assert tracks[0].full_id == "133993362_456242612_action_hash_url_hash"


def test_extract_audio_tracks_from_html_parses_mapping_data_audio() -> None:
    audio_data = {
        "owner_id": -2001247452,
        "id": 41247452,
        "url": "https://psv4.userapi.com/audio/file.m4a?token=value",
        "title": "Track",
        "artist": "Artist",
        "duration": 321,
        "actionHash": "action_hash",
        "urlHash": "url_hash",
    }
    escaped_audio_data = html_tools.escape(json.dumps(audio_data), quote=True)
    html = f'<button class="SecondaryAttachment" data-audio="{escaped_audio_data}"></button>'

    tracks = probe_vk_audio.extract_audio_tracks_from_html(html_text=html)

    assert len(tracks) == 1
    assert tracks[0].owner_id == "-2001247452"
    assert tracks[0].audio_id == "41247452"
    assert tracks[0].full_id == "-2001247452_41247452_action_hash_url_hash"


def test_extract_load_section_html_fragments_finds_nested_audio_html() -> None:
    payload = {
        "data": [
            {
                "list": '<div id="au_search_items"><div class="audio_item" data-audio="[1,2]"></div></div>',
                "hasMore": False,
            }
        ]
    }

    fragments = probe_vk_audio.extract_load_section_html_fragments(payload=payload)

    assert fragments == ('<div id="au_search_items"><div class="audio_item" data-audio="[1,2]"></div></div>',)


def test_extract_load_section_html_fragments_ignores_plain_text() -> None:
    payload = {"data": [{"list": "plain text without audio markup"}]}

    assert probe_vk_audio.extract_load_section_html_fragments(payload=payload) == ()


def test_extract_audio_data_texts_from_html_uses_regex_fallback() -> None:
    audio_data = [
        456242612,
        133993362,
        "https://psv4.userapi.com/audio/file.mp3?token=value",
        "Track title",
        "Artist",
        123,
    ]
    escaped_audio_data = html_tools.escape(json.dumps(audio_data), quote=True)
    html = f'<script>var markup = "data-audio=&quot;{escaped_audio_data}&quot;";</script>'

    values = probe_vk_audio.extract_audio_data_texts_from_html(html_text=html)

    assert values == (json.dumps(audio_data),)


def test_extract_audio_tracks_from_html_deduplicates_parser_and_scanner_results() -> None:
    audio_data = [
        456242612,
        133993362,
        "https://psv4.userapi.com/audio/file.mp3?token=value",
        "Track title",
        "Artist",
        123,
    ]
    escaped_audio_data = html_tools.escape(json.dumps(audio_data), quote=True)
    html = f'<div class="audio_item" data-audio="{escaped_audio_data}"></div>'

    tracks = probe_vk_audio.extract_audio_tracks_from_html(html_text=html)

    assert len(tracks) == 1


def test_parse_audio_data_json_repeatedly_unescapes_html() -> None:
    audio_data = [
        456242612,
        133993362,
        "https://psv4.userapi.com/audio/file.mp3?token=value",
        "Track title",
        "Artist",
        123,
    ]
    encoded_audio_data = html_tools.escape(
        html_tools.escape(json.dumps(audio_data), quote=True),
        quote=True,
    )

    parsed_audio_data = probe_vk_audio.parse_audio_data_json(value=encoded_audio_data)

    assert parsed_audio_data == audio_data


def test_build_track_diagnostic_source() -> None:
    audio_id = probe_vk_audio.VkAudioId(owner_id="133993362", audio_id="456242612")
    tracks = (
        probe_vk_audio.VkAudioTrack(owner_id="1", audio_id="2"),
        probe_vk_audio.VkAudioTrack(
            owner_id="133993362",
            audio_id="456242612",
            direct_url="https://psv4.userapi.com/audio/file.mp3",
            action_hash="action_hash",
            url_hash="url_hash",
        ),
    )

    source = probe_vk_audio.build_track_diagnostic_source(
        source="audio page",
        audio_id=audio_id,
        tracks=tracks,
    )

    assert source == "audio page tracks=2 matched=1 matched_hashes=1 matched_direct_urls=1 candidate_ids=1"


def test_extract_audio_tracks_from_mobile_reload_payload() -> None:
    payload = {
        "data": [
            [
                [
                    456242612,
                    133993362,
                    "https://psv4.userapi.com/audio/file.mp3?token=value",
                    "Track title",
                    "Artist",
                    123,
                ]
            ]
        ]
    }

    tracks = probe_vk_audio.extract_audio_tracks_from_mobile_reload_payload(payload=payload)

    assert len(tracks) == 1
    assert tracks[0].owner_id == "133993362"
    assert tracks[0].audio_id == "456242612"
    assert tracks[0].direct_url == "https://psv4.userapi.com/audio/file.mp3?token=value"


def test_select_direct_media_from_tracks_matches_target_audio_id() -> None:
    audio_id = probe_vk_audio.VkAudioId(owner_id="133993362", audio_id="456242612")
    tracks = (
        probe_vk_audio.VkAudioTrack(
            owner_id="1",
            audio_id="2",
            direct_url="https://psv4.userapi.com/audio/other.mp3",
        ),
        probe_vk_audio.VkAudioTrack(
            owner_id="133993362",
            audio_id="456242612",
            title="Track",
            artist="Artist",
            duration_seconds=123,
            direct_url="https://psv4.userapi.com/audio/file.mp3?token=value",
        ),
    )

    media = probe_vk_audio.select_direct_media_from_tracks(audio_id=audio_id, tracks=tracks)

    assert media is not None
    assert media.direct_url == "https://psv4.userapi.com/audio/file.mp3?token=value"
    assert media.title == "Track"
    assert media.artist == "Artist"
    assert media.duration_seconds == 123


def test_select_direct_media_from_tracks_converts_m3u8_to_mp3() -> None:
    audio_id = probe_vk_audio.VkAudioId(owner_id="133993362", audio_id="456242612")
    tracks = (
        probe_vk_audio.VkAudioTrack(
            owner_id="133993362",
            audio_id="456242612",
            direct_url="https://psv4.userapi.com/abc/audios/def/index.m3u8?token=value",
        ),
    )

    media = probe_vk_audio.select_direct_media_from_tracks(audio_id=audio_id, tracks=tracks)

    assert media is not None
    assert media.direct_url == "https://psv4.userapi.com/audios/def.mp3?token=value"


def test_extract_audio_tracks_from_mobile_reload_payload_recursively_parses_payload() -> None:
    payload = {
        "response": {
            "items": [
                [
                    456242612,
                    133993362,
                    "https://psv4.userapi.com/audio/file.mp3?token=value",
                    "Track title",
                    "Artist",
                    123,
                ]
            ]
        }
    }

    tracks = probe_vk_audio.extract_audio_tracks_from_mobile_reload_payload(payload=payload)

    assert len(tracks) == 1
    assert tracks[0].owner_id == "133993362"
    assert tracks[0].audio_id == "456242612"
    assert tracks[0].direct_url == "https://psv4.userapi.com/audio/file.mp3?token=value"


def test_build_full_id_candidates_for_reused_vk_audio() -> None:
    track = probe_vk_audio.VkAudioTrack(
        owner_id="133993362",
        audio_id="456242612",
        action_hash="action_hash",
        url_hash="url_hash",
        playback_hash="playback_hash",
        access_key="access_key",
        source_owner_id="-2001247452",
        source_audio_id="41247452",
    )

    candidates = probe_vk_audio.build_full_id_candidates(track=track)

    assert candidates == (
        "133993362_456242612_action_hash_url_hash",
        "133993362_456242612_playback_hash_access_key",
        "133993362_456242612_action_hash_access_key",
        "133993362_456242612_playback_hash_url_hash",
        "-2001247452_41247452_action_hash_url_hash",
        "-2001247452_41247452_playback_hash_access_key",
        "-2001247452_41247452_action_hash_access_key",
        "-2001247452_41247452_playback_hash_url_hash",
    )


def test_parse_vk_audio_track_from_sequence_extracts_reused_audio_fields() -> None:
    audio_data = [
        456242612,
        133993362,
        "",
        "Death Note",
        "Polyphia feat. Ichika",
        220,
        0,
        0,
        "",
        0,
        98,
        "",
        "[]",
        "85595a0e8936466b24//c5d33322bb972c7175///3da835e94c38e31259/",
        "",
        {"duration": 220, "content_id": "133993362_456242612"},
        "",
        [],
        [],
        [],
        "playback_hash",
        0,
        0,
        True,
        "access_key",
        False,
        "-2001247452_41247452",
    ]

    track = probe_vk_audio.parse_vk_audio_track_from_sequence(value=audio_data)

    assert track is not None
    assert track.action_hash == "c5d33322bb972c7175"
    assert track.url_hash == "3da835e94c38e31259"
    assert track.playback_hash == "playback_hash"
    assert track.access_key == "access_key"
    assert track.source_owner_id == "-2001247452"
    assert track.source_audio_id == "41247452"


def test_decode_vk_audio_api_unavailable_url_decodes_reverse_operation() -> None:
    direct_url = "https://psv4.userapi.com/audio/file.mp3?token=value"
    encoded_url = build_encoded_audio_api_unavailable_url(direct_url=direct_url)

    assert probe_vk_audio.decode_vk_audio_api_unavailable_url(url=encoded_url, user_id=87387839) == direct_url


def test_parse_vk_audio_track_from_sequence_decodes_audio_api_unavailable_url() -> None:
    direct_url = "https://psv4.userapi.com/audio/file.mp3?token=value"
    encoded_url = build_encoded_audio_api_unavailable_url(direct_url=direct_url)
    audio_data = [
        456242612,
        133993362,
        encoded_url,
        "Death Note",
        "Polyphia feat. Ichika",
        220,
        0,
        0,
        "",
        0,
        98,
        "",
        "[]",
        "85595a0e8936466b24//c5d33322bb972c7175///3da835e94c38e31259/",
        "",
        {"duration": 220, "content_id": "133993362_456242612", "vk_id": 87387839},
    ]

    track = probe_vk_audio.parse_vk_audio_track_from_sequence(value=audio_data)

    assert track is not None
    assert track.direct_url == direct_url
    assert track.user_id == 87387839


def test_find_direct_audio_url_in_nested_payload() -> None:
    payload = {
        "payload": [
            0,
            [
                [
                    41247452,
                    -2001247452,
                    "https://psv4.userapi.com/audio/file.m4a?extra=value",
                    "Track title",
                    "Artist",
                ]
            ],
        ]
    }

    assert probe_vk_audio.find_direct_audio_url(value=payload) == (
        "https://psv4.userapi.com/audio/file.m4a?extra=value"
    )


def test_find_direct_audio_url_extracts_embedded_url_from_text() -> None:
    payload = {
        "payload": [
            'player({"url":"https:\\/\\/psv4.userapi.com\\/audio\\/file.mp3?extra=value"})',
        ]
    }

    assert probe_vk_audio.find_direct_audio_url(value=payload) == (
        "https://psv4.userapi.com/audio/file.mp3?extra=value"
    )


def test_find_direct_audio_url_normalizes_protocol_relative_url() -> None:
    assert probe_vk_audio.find_direct_audio_url(value="//psv4.userapi.com/audio/file.mp3?x=1") == (
        "https://psv4.userapi.com/audio/file.mp3?x=1"
    )


def test_find_direct_audio_url_ignores_audio_api_unavailable() -> None:
    payload = {
        "payload": [
            "https://vk.com/mp3/audio_api_unavailable.mp3",
            "Track title",
        ]
    }

    assert probe_vk_audio.find_direct_audio_url(value=payload) is None
    assert probe_vk_audio.find_string_containing(value=payload, needle="audio_api_unavailable") is not None


def test_find_direct_audio_url_rejects_android_app_audio_link() -> None:
    payload = {
        "payload": [
            "android-app://com.vkontakte.android/vkontakte/m.vk.com/audio",
            "//com.vkontakte.android/vkontakte/m.vk.com/audio",
        ]
    }

    assert probe_vk_audio.find_direct_audio_url(value=payload) is None


def test_find_direct_audio_url_rejects_vk_audio_page_link() -> None:
    payload = {
        "payload": [
            "https://m.vk.com/audio",
            "https://vk.com/audio133993362_456242612_cb6b8410a741a6993a",
        ]
    }

    assert probe_vk_audio.find_direct_audio_url(value=payload) is None


def test_find_direct_audio_url_accepts_userapi_audio_cdn_url() -> None:
    payload = {
        "payload": [
            "https://psv4.userapi.com/audio/file_without_extension?token=value",
        ]
    }

    assert probe_vk_audio.find_direct_audio_url(value=payload) == (
        "https://psv4.userapi.com/audio/file_without_extension?token=value"
    )


def test_build_dump_response_marker_diagnostics_text() -> None:
    diagnostics_text = probe_vk_audio.build_dump_response_marker_diagnostics_text(
        response_dump_parts=(
            (
                "mobile load_section",
                '<div class="audio_item" data-audio="[1,2]"></div>',
            ),
            (
                "desktop reload_audio",
                '{"payload":["\\"bad_hash\\""]}',
            ),
        ),
    )

    assert "mobile load_section: length=" in diagnostics_text
    assert "data_audio=True" in diagnostics_text
    assert "audio_item=True" in diagnostics_text
    assert "bad_hash=True" in diagnostics_text


def test_build_response_diagnostics_detects_bad_hash() -> None:
    diagnostics = probe_vk_audio.build_response_diagnostics(
        source="reload_audio",
        value={"payload": ['"bad_hash"']},
        raw_text='{"payload":["\\"bad_hash\\""]}',
    )

    assert diagnostics.has_bad_hash is True


def test_build_response_diagnostics_redacts_url_preview() -> None:
    diagnostics = probe_vk_audio.build_response_diagnostics(
        source="test",
        value={"payload": ["https://example.com/audio.mp3?token=secret"]},
        raw_text='{"payload":["https://example.com/audio.mp3?token=secret"]}',
    )

    assert diagnostics.source == "test"
    assert diagnostics.embedded_url_candidates_count == 1
    assert diagnostics.has_bad_hash is False
    assert "<redacted-url>" in diagnostics.safe_preview
    assert "token=secret" not in diagnostics.safe_preview


def test_redact_url_query() -> None:
    assert probe_vk_audio.redact_url_query(url="https://example.com/audio.mp3?token=secret") == (
        "https://example.com/audio.mp3?<redacted>"
    )


def test_resolve_audio_extension() -> None:
    assert probe_vk_audio.resolve_audio_extension(url="https://example.com/file.m4a?x=1") == ".m4a"
    assert probe_vk_audio.resolve_audio_extension(url="https://example.com/file") == ".mp3"


def test_is_hls_playlist_url_detects_m3u8() -> None:
    assert probe_vk_audio.is_hls_playlist_url(url="https://example.com/index.m3u8?token=value") is True
    assert probe_vk_audio.is_hls_playlist_url(url="https://example.com/audio.mp3?token=value") is False


def test_resolve_output_extension_uses_requested_format_for_hls() -> None:
    assert (
        probe_vk_audio.resolve_output_extension(
            url="https://example.com/index.m3u8?token=value",
            output_format="mp3",
        )
        == ".mp3"
    )
    assert (
        probe_vk_audio.resolve_output_extension(
            url="https://example.com/index.m3u8?token=value",
            output_format="m4a",
        )
        == ".m4a"
    )


def test_resolve_ffmpeg_executable_accepts_explicit_file(tmp_path: Path) -> None:
    ffmpeg_path = tmp_path / "ffmpeg.exe"
    ffmpeg_path.write_text("", encoding="utf-8")

    assert probe_vk_audio.resolve_ffmpeg_executable(ffmpeg_path=ffmpeg_path) == ffmpeg_path.resolve()


def test_build_ffmpeg_hls_download_command_uses_headers_and_codec(tmp_path: Path) -> None:
    ffmpeg_path = tmp_path / "ffmpeg.exe"
    output_path = tmp_path / "audio.mp3"

    command = probe_vk_audio.build_ffmpeg_hls_download_command(
        ffmpeg_executable=ffmpeg_path,
        media_url="https://example.com/index.m3u8?token=value",
        output_path=output_path,
        output_format="mp3",
    )

    assert command[0] == str(ffmpeg_path)
    assert "-headers" in command
    assert "User-Agent:" in command[command.index("-headers") + 1]
    assert "libmp3lame" in command
    assert command[-1] == str(output_path)


def test_build_output_file_stem_uses_track_title() -> None:
    media = probe_vk_audio.VkAudioDirectMedia(
        audio_id=probe_vk_audio.VkAudioId(owner_id="1", audio_id="2"),
        direct_url="https://example.com/audio.mp3",
        artist="Artist",
        title="Track",
    )

    assert probe_vk_audio.build_output_file_stem(media=media) == "Artist - Track"


def test_build_output_file_stem_falls_back_to_audio_id() -> None:
    media = probe_vk_audio.VkAudioDirectMedia(
        audio_id=probe_vk_audio.VkAudioId(owner_id="1", audio_id="2"),
        direct_url="https://example.com/audio.mp3",
    )

    assert probe_vk_audio.build_output_file_stem(media=media) == "vk_audio_1_2"
