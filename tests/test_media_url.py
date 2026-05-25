from __future__ import annotations

import pytest

from yaloader.domain.value_objects.media_url import MediaUrl


def test_media_url_normalizes_spaces() -> None:
    media_url = MediaUrl(" https://www.youtube.com/watch?v=test ")

    assert media_url.value == "https://www.youtube.com/watch?v=test"


def test_media_url_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        MediaUrl("   ")


def test_media_url_rejects_non_http_scheme() -> None:
    with pytest.raises(ValueError, match="http or https"):
        MediaUrl("ftp://example.com/video")


def test_media_url_rejects_missing_host() -> None:
    with pytest.raises(ValueError, match="host"):
        MediaUrl("https:///watch")
