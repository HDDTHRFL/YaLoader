from __future__ import annotations

import importlib.util
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


def test_parse_vk_audio_id_from_vk_url() -> None:
    audio_id = probe_vk_audio.parse_vk_audio_id(url="https://vk.com/audio-2001247452_41247452")

    assert audio_id.owner_id == "-2001247452"
    assert audio_id.audio_id == "41247452"
    assert audio_id.access_key is None
    assert audio_id.value == "-2001247452_41247452"
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


def test_parse_vk_al_json_payload_with_html_comment_prefix() -> None:
    payload = probe_vk_audio.parse_vk_al_json_payload(
        text='<!--{"payload":[["https:\\/\\/example.com\\/audio.mp3?x=1"]]}',
    )

    assert isinstance(payload, dict)
    assert probe_vk_audio.find_direct_audio_url(value=payload) == "https://example.com/audio.mp3?x=1"


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


def test_build_response_diagnostics_detects_bad_hash() -> None:
    diagnostics = probe_vk_audio.build_response_diagnostics(
        source="reload_audio",
        value={"payload": ['"bad_hash"']},
        raw_text='{"payload":["\\"bad_hash\\""]}',
    )

    assert diagnostics.has_bad_hash is True


def test_redact_url_query() -> None:
    assert probe_vk_audio.redact_url_query(url="https://example.com/audio.mp3?token=secret") == (
        "https://example.com/audio.mp3?<redacted>"
    )


def test_resolve_audio_extension() -> None:
    assert probe_vk_audio.resolve_audio_extension(url="https://example.com/file.m4a?x=1") == ".m4a"
    assert probe_vk_audio.resolve_audio_extension(url="https://example.com/file") == ".mp3"
