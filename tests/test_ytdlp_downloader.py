from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from yaloader.application.dto.download_result import DownloadResult
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.domain.value_objects.media_url import MediaUrl
from yaloader.infrastructure.ytdlp.downloader import YtDlpDownloader
from yaloader.infrastructure.ytdlp.options_builder import YtDlpOptions, YtDlpOptionsBuilder


class RecordingYtDlpBackend:
    def __init__(self) -> None:
        self.urls: tuple[str, ...] = ()
        self.options: YtDlpOptions | None = None

    def download(self, urls: Sequence[str], options: YtDlpOptions) -> None:
        self.urls = tuple(urls)
        self.options = options


class FailingYtDlpBackend:
    def download(self, urls: Sequence[str], options: YtDlpOptions) -> None:
        raise RuntimeError("download failed")


def test_ytdlp_downloader_returns_completed_result(tmp_path: Path) -> None:
    backend = RecordingYtDlpBackend()
    downloader = YtDlpDownloader(
        options_builder=YtDlpOptionsBuilder(),
        backend=backend,
    )
    task = create_video_task(target_dir=tmp_path)

    result = downloader.download(task=task)

    assert isinstance(result, DownloadResult)
    assert result.task_id == task.task_id
    assert result.status == DownloadStatus.COMPLETED
    assert result.error_message is None
    assert backend.urls == (task.url.value,)
    assert backend.options is not None
    assert backend.options["merge_output_format"] == "mp4"


def test_ytdlp_downloader_returns_failed_result_on_backend_error(tmp_path: Path) -> None:
    downloader = YtDlpDownloader(
        options_builder=YtDlpOptionsBuilder(),
        backend=FailingYtDlpBackend(),
    )
    task = create_video_task(target_dir=tmp_path)

    result = downloader.download(task=task)

    assert result.task_id == task.task_id
    assert result.status == DownloadStatus.FAILED
    assert result.error_message == "download failed"


def create_video_task(target_dir: Path) -> DownloadTask:
    return DownloadTask.create(
        url=MediaUrl("https://www.youtube.com/watch?v=test"),
        target_dir=target_dir,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
        include_playlist=False,
    )
