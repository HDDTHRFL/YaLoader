from __future__ import annotations

import pytest

from yaloader.infrastructure.ytdlp.version_checker import (
    YtDlpVersionCheckError,
    extract_latest_version_from_pypi_payload,
)


def test_extract_latest_version_from_pypi_payload_returns_version() -> None:
    version = extract_latest_version_from_pypi_payload(
        payload={
            "info": {
                "version": "2026.3.17",
            },
        },
    )

    assert version == "2026.3.17"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"info": {}},
        {"info": {"version": ""}},
        {"info": {"version": 123}},
    ],
)
def test_extract_latest_version_from_pypi_payload_rejects_invalid_payload(
    payload: object,
) -> None:
    with pytest.raises(YtDlpVersionCheckError):
        extract_latest_version_from_pypi_payload(payload=payload)
