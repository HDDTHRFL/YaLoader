from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Self

import pytest

from yaloader.application.ports.downloader import CancellationToken
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality
from yaloader.domain.value_objects.media_url import MediaUrl
from yaloader.infrastructure.ytdlp.download_preparer import (
    DownloadPreparationCancelledError,
    YtDlpDownloadPreparer,
)
from yaloader.infrastructure.ytdlp.options_builder import YtDlpOptions, YtDlpOptionsBuilder


class FakeYoutubeDLPreparationRuntime:
    def __init__(self, *, raw_info: object) -> None:
        self.raw_info = raw_info
        self.extract_url: str | None = None
        self.extract_download: bool | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return None

    def extract_info(self, url: str, download: bool = False) -> object:
        self.extract_url = url
        self.extract_download = download

        return self.raw_info


class FakeYoutubeDLPreparationFactory:
    def __init__(self, *, runtime: FakeYoutubeDLPreparationRuntime) -> None:
        self.runtime = runtime
        self.params: YtDlpOptions | None = None

    def __call__(self, params: YtDlpOptions) -> FakeYoutubeDLPreparationRuntime:
        self.params = params

        return self.runtime


class AlwaysCanceledToken:
    @property
    def is_cancel_requested(self) -> bool:
        return True


def test_preparer_extracts_video_info_without_download(tmp_path: Path) -> None:
    runtime = FakeYoutubeDLPreparationRuntime(
        raw_info={
            "title": "Test video",
            "duration": 100,
            "formats": [
                {
                    "format_id": "url1080",
                    "ext": "mp4",
                    "vcodec": "h264",
                    "acodec": "aac",
                    "tbr": 1000,
                }
            ],
        },
    )
    factory = FakeYoutubeDLPreparationFactory(runtime=runtime)
    task = create_task(target_dir=tmp_path, include_playlist=False)
    preparer = YtDlpDownloadPreparer(
        youtube_dl_factory=factory,
        options_builder=YtDlpOptionsBuilder(),
    )

    prepared_download = preparer.prepare(task=task)

    assert prepared_download.task_id == task.task_id
    assert prepared_download.url == task.url.value
    assert prepared_download.title == "Test video"
    assert prepared_download.playlist_count is None
    assert prepared_download.raw_info["title"] == "Test video"
    assert prepared_download.estimated_file_size_bytes == 12_500_000
    assert prepared_download.is_file_size_estimated is True
    assert runtime.extract_url == task.url.value
    assert runtime.extract_download is False

    assert factory.params is not None
    assert factory.params["skip_download"] is True
    assert factory.params["simulate"] is True
    assert factory.params["noplaylist"] is True


def test_preparer_extracts_playlist_info_without_download(tmp_path: Path) -> None:
    runtime = FakeYoutubeDLPreparationRuntime(
        raw_info={
            "title": "Test playlist",
            "entries": [
                {"id": "first"},
                {"id": "second"},
            ],
        },
    )
    factory = FakeYoutubeDLPreparationFactory(runtime=runtime)
    task = create_task(target_dir=tmp_path, include_playlist=True)
    preparer = YtDlpDownloadPreparer(
        youtube_dl_factory=factory,
        options_builder=YtDlpOptionsBuilder(),
    )

    prepared_download = preparer.prepare(task=task)

    assert prepared_download.title == "Test playlist"
    assert prepared_download.playlist_count == 2

    assert factory.params is not None
    assert factory.params["skip_download"] is True
    assert factory.params["simulate"] is True
    assert factory.params["noplaylist"] is False


def test_preparer_respects_cancellation_before_extraction(tmp_path: Path) -> None:
    runtime = FakeYoutubeDLPreparationRuntime(raw_info={"title": "Test video"})
    factory = FakeYoutubeDLPreparationFactory(runtime=runtime)
    task = create_task(target_dir=tmp_path, include_playlist=False)
    preparer = YtDlpDownloadPreparer(
        youtube_dl_factory=factory,
        options_builder=YtDlpOptionsBuilder(),
    )
    cancellation_token: CancellationToken = AlwaysCanceledToken()

    with pytest.raises(DownloadPreparationCancelledError):
        preparer.prepare(
            task=task,
            cancellation_token=cancellation_token,
        )

    assert runtime.extract_url is None


def create_task(*, target_dir: Path, include_playlist: bool) -> DownloadTask:
    return DownloadTask.create(
        url=MediaUrl(value="https://www.youtube.com/watch?v=test001"),
        target_dir=target_dir,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
        include_playlist=include_playlist,
    )
