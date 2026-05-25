from __future__ import annotations

from pathlib import Path

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality
from yaloader.infrastructure.ytdlp.options_builder import YtDlpOptionsBuilder


def test_build_video_mp4_best_options(tmp_path: Path) -> None:
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
    )
    builder = YtDlpOptionsBuilder()

    options = builder.build(request=request)

    assert options["format"] == "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
    assert options["merge_output_format"] == "mp4"
    assert options["noplaylist"] is True
    assert options["remote_components"] == ["ejs:github"]
    assert str(tmp_path) in str(options["outtmpl"])


def test_build_video_webm_1080p_options(tmp_path: Path) -> None:
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.WEBM,
        video_quality=VideoQuality.P1080,
    )
    builder = YtDlpOptionsBuilder()

    options = builder.build(request=request)

    assert "[height<=1080]" in str(options["format"])
    assert options["merge_output_format"] == "webm"


def test_build_audio_mp3_options(tmp_path: Path) -> None:
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        mode=DownloadMode.AUDIO,
        output_format=OutputFormat.MP3,
    )
    builder = YtDlpOptionsBuilder()

    options = builder.build(request=request)

    assert options["format"] == "ba/b"
    assert "merge_output_format" not in options
    assert options["remote_components"] == ["ejs:github"]
    assert options["postprocessors"] == [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "0",
        }
    ]


def test_build_audio_m4a_options(tmp_path: Path) -> None:
    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        mode=DownloadMode.AUDIO,
        output_format=OutputFormat.M4A,
    )
    builder = YtDlpOptionsBuilder()

    options = builder.build(request=request)

    assert options["format"] == "ba[ext=m4a]/ba/b"
    assert options["postprocessors"] == [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
        }
    ]


def test_build_playlist_options(tmp_path: Path) -> None:
    request = DownloadRequest(
        url="https://www.youtube.com/playlist?list=test",
        target_dir=tmp_path,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        include_playlist=True,
    )
    builder = YtDlpOptionsBuilder()

    options = builder.build(request=request)

    assert options["noplaylist"] is False


def test_build_adds_cookiefile_when_cookies_file_exists(tmp_path: Path) -> None:
    cookies_file = tmp_path / "cookies.txt"
    cookies_file.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
    )
    builder = YtDlpOptionsBuilder(cookies_file=cookies_file)

    options = builder.build(request=request)

    assert options["cookiefile"] == str(cookies_file)


def test_build_skips_cookiefile_when_cookies_file_is_missing(tmp_path: Path) -> None:
    cookies_file = tmp_path / "cookies.txt"

    request = DownloadRequest(
        url="https://www.youtube.com/watch?v=test",
        target_dir=tmp_path,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
    )
    builder = YtDlpOptionsBuilder(cookies_file=cookies_file)

    options = builder.build(request=request)

    assert "cookiefile" not in options
