from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality


def test_download_request_accepts_valid_video_request(tmp_path: Path) -> None:
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


def test_download_request_accepts_valid_audio_request(tmp_path: Path) -> None:
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        mode=DownloadMode.AUDIO,
        output_format=OutputFormat.MP3,
    )

    assert request.mode == DownloadMode.AUDIO
    assert request.output_format == OutputFormat.MP3


def test_download_request_accepts_youtube_short_url(tmp_path: Path) -> None:
    request = DownloadRequest(
        url="https://youtu.be/test",
        target_dir=tmp_path,
    )

    assert request.url == "https://youtu.be/test"


def test_download_request_rejects_invalid_url(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        DownloadRequest(
            url="not-a-url",
            target_dir=tmp_path,
        )


def test_download_request_rejects_unsupported_host(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        DownloadRequest(
            url="https://example.com/video",
            target_dir=tmp_path,
        )


def test_download_request_rejects_relative_target_dir() -> None:
    with pytest.raises(ValidationError):
        DownloadRequest(
            url="https://www.youtube.com/watch?v=test",
            target_dir=Path("downloads"),
        )


def test_download_request_rejects_audio_format_for_video_mode(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        DownloadRequest(
            url="https://www.youtube.com/watch?v=test",
            target_dir=tmp_path,
            mode=DownloadMode.VIDEO,
            output_format=OutputFormat.MP3,
        )


def test_download_request_rejects_video_format_for_audio_mode(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        DownloadRequest(
            url="https://www.youtube.com/watch?v=test",
            target_dir=tmp_path,
            mode=DownloadMode.AUDIO,
            output_format=OutputFormat.MP4,
        )


def test_download_request_accepts_download_speed_limit(tmp_path: Path) -> None:
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        download_speed_limit_bytes_per_second=1_048_576,
    )

    assert request.download_speed_limit_bytes_per_second == 1_048_576


def test_download_request_rejects_negative_download_speed_limit(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        DownloadRequest(
            url="https://www.youtube.com/watch?v=test",
            target_dir=tmp_path,
            download_speed_limit_bytes_per_second=-1,
        )
