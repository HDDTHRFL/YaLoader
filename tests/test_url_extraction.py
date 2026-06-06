from __future__ import annotations

from yaloader.domain.url_extraction import (
    extract_first_http_url,
    extract_first_http_url_from_candidates,
    is_http_url,
    normalize_url_candidate,
)


def test_extract_first_http_url_from_plain_url() -> None:
    assert (
        extract_first_http_url(text="https://www.youtube.com/watch?v=test")
        == "https://www.youtube.com/watch?v=test"
    )


def test_extract_first_http_url_from_text() -> None:
    assert (
        extract_first_http_url(text="Видео тут: https://youtu.be/test123")
        == "https://youtu.be/test123"
    )


def test_extract_first_http_url_strips_trailing_punctuation() -> None:
    assert (
        extract_first_http_url(text="Ссылка: https://www.youtube.com/watch?v=test.")
        == "https://www.youtube.com/watch?v=test"
    )


def test_extract_first_http_url_returns_none_without_url() -> None:
    assert extract_first_http_url(text="тут нет ссылки") is None


def test_extract_first_http_url_from_candidates_uses_first_valid_url() -> None:
    assert (
        extract_first_http_url_from_candidates(
            candidates=(
                "plain text",
                "https://youtu.be/video-id",
                "https://www.youtube.com/watch?v=second",
            )
        )
        == "https://youtu.be/video-id"
    )


def test_extract_first_http_url_from_candidates_extracts_url_from_mixed_text() -> None:
    assert (
        extract_first_http_url_from_candidates(
            candidates=(
                "Открой это видео: https://www.youtube.com/watch?v=abc123",
                "https://www.youtube.com/watch?v=second",
            )
        )
        == "https://www.youtube.com/watch?v=abc123"
    )


def test_normalize_url_candidate_strips_spaces_and_punctuation() -> None:
    assert (
        normalize_url_candidate(candidate="  https://www.youtube.com/watch?v=test),  ")
        == "https://www.youtube.com/watch?v=test"
    )


def test_is_http_url_accepts_http_and_https() -> None:
    assert is_http_url(text="http://example.com")
    assert is_http_url(text="https://example.com")


def test_is_http_url_rejects_non_http_url() -> None:
    assert not is_http_url(text="file:///C:/video.mp4")
