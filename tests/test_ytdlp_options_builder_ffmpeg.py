from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.infrastructure.ytdlp.options_builder import YtDlpOptionsBuilder


@dataclass(frozen=True, slots=True)
class FakeProcessRunner:
    executable_path: Path | None

    def find_executable(self, executable_name: str) -> Path | None:
        if executable_name != "ffmpeg":
            return None

        return self.executable_path


def test_options_builder_adds_ffmpeg_location_when_ffmpeg_is_found(tmp_path: Path) -> None:
    ffmpeg_path = tmp_path / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
    ffmpeg_path.parent.mkdir(parents=True)
    ffmpeg_path.write_text("fake ffmpeg", encoding="utf-8")

    options = YtDlpOptionsBuilder(
        process_runner=FakeProcessRunner(executable_path=ffmpeg_path),
    ).build(
        request=create_video_request(tmp_path=tmp_path),
    )

    assert options["ffmpeg_location"] == str(ffmpeg_path)


def test_options_builder_skips_ffmpeg_location_when_ffmpeg_is_missing(tmp_path: Path) -> None:
    options = YtDlpOptionsBuilder(
        process_runner=FakeProcessRunner(executable_path=None),
    ).build(
        request=create_video_request(tmp_path=tmp_path),
    )

    assert "ffmpeg_location" not in options


def test_options_builder_keeps_working_without_process_runner(tmp_path: Path) -> None:
    options = YtDlpOptionsBuilder().build(
        request=create_video_request(tmp_path=tmp_path),
    )

    assert "ffmpeg_location" not in options


def create_video_request(*, tmp_path: Path) -> DownloadRequest:
    return DownloadRequest(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        target_dir=tmp_path,
    )
