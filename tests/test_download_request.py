from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality


def test_download_request_accepts_valid_absolute_target_dir(tmp_path: Path) -> None:
    request = DownloadRequest(
        url=" https://www.youtube.com/watch?v=test ",
        target_dir=tmp_path,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )

    assert request.url == "https://www.youtube.com/watch?v=test"
    assert request.target_dir == tmp_path
    assert request.mode == DownloadMode.VIDEO
    assert request.output_format == OutputFormat.MP4
    assert request.video_quality == VideoQuality.BEST


def test_download_request_rejects_invalid_url(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        DownloadRequest(
            url="not-a-url",
            target_dir=tmp_path,
        )


def test_download_request_rejects_relative_target_dir() -> None:
    with pytest.raises(ValidationError):
        DownloadRequest(
            url="https://www.youtube.com/watch?v=test",
            target_dir=Path("downloads"),
        )
