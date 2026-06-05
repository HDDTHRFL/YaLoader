from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.dto.prepared_download import PreparedDownload
from yaloader.application.services.prepared_download_cache import PreparedDownloadCache
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.domain.value_objects.media_url import MediaUrl
from yaloader.infrastructure.ytdlp.downloader import (
    YtDlpDownloader,
    calculate_percent,
    strip_ansi_escape_sequences,
)
from yaloader.infrastructure.ytdlp.options_builder import YtDlpOptions, YtDlpOptionsBuilder


class RecordingYtDlpBackend:
    def __init__(self) -> None:
        self.urls: tuple[str, ...] = ()
        self.options: YtDlpOptions | None = None
        self.prepared_download: PreparedDownload | None = None

    def download(self, urls: Sequence[str], options: YtDlpOptions) -> None:
        self.urls = tuple(urls)
        self.options = options

    def download_prepared(
        self,
        *,
        prepared_download: PreparedDownload,
        options: YtDlpOptions,
    ) -> None:
        self.prepared_download = prepared_download
        self.options = options


class CreatingOutputYtDlpBackend:
    def __init__(self, *, output_file_name: str = "downloaded.mp4") -> None:
        self.output_file_name = output_file_name

    def download(self, urls: Sequence[str], options: YtDlpOptions) -> None:
        target_dir = get_target_dir_from_options(options=options)
        (target_dir / self.output_file_name).write_text("video", encoding="utf-8")

    def download_prepared(
        self,
        *,
        prepared_download: PreparedDownload,
        options: YtDlpOptions,
    ) -> None:
        target_dir = get_target_dir_from_options(options=options)
        (target_dir / self.output_file_name).write_text("video", encoding="utf-8")


class FailingYtDlpBackend:
    def download(self, urls: Sequence[str], options: YtDlpOptions) -> None:
        raise RuntimeError("download failed")


class BotCheckYtDlpBackend:
    def download(self, urls: Sequence[str], options: YtDlpOptions) -> None:
        raise RuntimeError(
            "\x1b[0;31mERROR:\x1b[0m [youtube] test: Sign in to confirm you're not a bot."
        )


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


def test_ytdlp_downloader_returns_created_output_path(tmp_path: Path) -> None:
    backend = CreatingOutputYtDlpBackend(output_file_name="created-video.mp4")
    downloader = YtDlpDownloader(
        options_builder=YtDlpOptionsBuilder(),
        backend=backend,
    )
    task = create_video_task(target_dir=tmp_path)

    result = downloader.download(task=task)

    assert result.status == DownloadStatus.COMPLETED
    assert result.output_path == (tmp_path / "created-video.mp4").resolve()


def test_ytdlp_downloader_ignores_existing_files_for_output_path(tmp_path: Path) -> None:
    existing_file = tmp_path / "already-existed.mp4"
    existing_file.write_text("old", encoding="utf-8")
    backend = CreatingOutputYtDlpBackend(output_file_name="new-video.mp4")
    downloader = YtDlpDownloader(
        options_builder=YtDlpOptionsBuilder(),
        backend=backend,
    )
    task = create_video_task(target_dir=tmp_path)

    result = downloader.download(task=task)

    assert result.status == DownloadStatus.COMPLETED
    assert result.output_path == (tmp_path / "new-video.mp4").resolve()


def test_ytdlp_downloader_adds_progress_hook_when_callback_is_passed(tmp_path: Path) -> None:
    backend = RecordingYtDlpBackend()
    downloader = YtDlpDownloader(
        options_builder=YtDlpOptionsBuilder(),
        backend=backend,
    )
    task = create_video_task(target_dir=tmp_path)
    progress_events: list[DownloadProgress] = []

    result = downloader.download(
        task=task,
        progress_callback=progress_events.append,
    )

    assert result.status == DownloadStatus.COMPLETED
    assert backend.options is not None
    assert "progress_hooks" in backend.options
    assert progress_events[0] == DownloadProgress.started(task_id=task.task_id)
    assert progress_events[-1] == DownloadProgress.completed(task_id=task.task_id)


def test_ytdlp_downloader_uses_prepared_download_from_cache(tmp_path: Path) -> None:
    backend = RecordingYtDlpBackend()
    prepared_download_cache = PreparedDownloadCache()
    downloader = YtDlpDownloader(
        options_builder=YtDlpOptionsBuilder(),
        backend=backend,
        prepared_download_cache=prepared_download_cache,
    )
    task = create_video_task(target_dir=tmp_path)
    prepared_download = PreparedDownload(
        task_id=task.task_id,
        url=task.url.value,
        title="Prepared video",
        raw_info={
            "id": "test",
            "title": "Prepared video",
        },
    )
    prepared_download_cache.save(prepared_download=prepared_download)

    result = downloader.download(task=task)

    assert result.status == DownloadStatus.COMPLETED
    assert backend.urls == ()
    assert backend.prepared_download == prepared_download
    assert backend.options is not None
    assert backend.options["merge_output_format"] == "mp4"


def test_ytdlp_downloader_uses_unique_prepared_output_template_for_duplicate_file(
    tmp_path: Path,
) -> None:
    existing_file = tmp_path / "Prepared video.mp4"
    existing_file.write_text("old", encoding="utf-8")
    backend = RecordingYtDlpBackend()
    prepared_download_cache = PreparedDownloadCache()
    downloader = YtDlpDownloader(
        options_builder=YtDlpOptionsBuilder(),
        backend=backend,
        prepared_download_cache=prepared_download_cache,
    )
    task = create_video_task(target_dir=tmp_path)
    prepared_download = PreparedDownload(
        task_id=task.task_id,
        url=task.url.value,
        title="Prepared video",
        raw_info={"title": "Prepared video"},
    )
    prepared_download_cache.save(prepared_download=prepared_download)

    result = downloader.download(task=task)

    assert result.status == DownloadStatus.COMPLETED
    assert backend.options is not None
    assert str(backend.options["outtmpl"]).endswith("Prepared video (1).%(ext)s")


def test_ytdlp_downloader_removes_generated_id_suffix_from_prepared_output_template(
    tmp_path: Path,
) -> None:
    backend = RecordingYtDlpBackend()
    prepared_download_cache = PreparedDownloadCache()
    downloader = YtDlpDownloader(
        options_builder=YtDlpOptionsBuilder(),
        backend=backend,
        prepared_download_cache=prepared_download_cache,
    )
    task = create_video_task(target_dir=tmp_path)
    prepared_download = PreparedDownload(
        task_id=task.task_id,
        url=task.url.value,
        title="Wanderbelle [TedhnnoEqiz]",
        raw_info={"title": "Wanderbelle [TedhnnoEqiz]"},
    )
    prepared_download_cache.save(prepared_download=prepared_download)

    result = downloader.download(task=task)

    assert result.status == DownloadStatus.COMPLETED
    assert backend.options is not None
    output_template = str(backend.options["outtmpl"])
    assert output_template.endswith("Wanderbelle.%(ext)s")
    assert "TedhnnoEqiz" not in output_template


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


def test_ytdlp_downloader_reports_failed_progress_on_backend_error(tmp_path: Path) -> None:
    downloader = YtDlpDownloader(
        options_builder=YtDlpOptionsBuilder(),
        backend=FailingYtDlpBackend(),
    )
    task = create_video_task(target_dir=tmp_path)
    progress_events: list[DownloadProgress] = []

    result = downloader.download(
        task=task,
        progress_callback=progress_events.append,
    )

    assert result.status == DownloadStatus.FAILED
    assert progress_events[-1] == DownloadProgress.failed(task_id=task.task_id)


def test_ytdlp_downloader_returns_friendly_bot_check_error(tmp_path: Path) -> None:
    cookies_file = tmp_path / "cookies.txt"
    downloader = YtDlpDownloader(
        options_builder=YtDlpOptionsBuilder(cookies_file=cookies_file),
        backend=BotCheckYtDlpBackend(),
        cookies_file=cookies_file,
    )
    task = create_video_task(target_dir=tmp_path)

    result = downloader.download(task=task)

    assert result.status == DownloadStatus.FAILED
    assert result.error_message is not None
    assert "YouTube запросил подтверждение" in result.error_message
    assert str(cookies_file) in result.error_message
    assert "\x1b" not in result.error_message


def test_calculate_percent_returns_none_for_missing_values() -> None:
    assert calculate_percent(downloaded_bytes=None, total_bytes=100) is None
    assert calculate_percent(downloaded_bytes=50, total_bytes=None) is None
    assert calculate_percent(downloaded_bytes=50, total_bytes=0) is None


def test_calculate_percent_calculates_valid_percent() -> None:
    assert calculate_percent(downloaded_bytes=50, total_bytes=200) == 25


def test_strip_ansi_escape_sequences_removes_color_codes() -> None:
    text = "\x1b[0;31mERROR:\x1b[0m failed"

    result = strip_ansi_escape_sequences(text=text)

    assert result == "ERROR: failed"


def get_target_dir_from_options(*, options: YtDlpOptions) -> Path:
    output_template = options.get("outtmpl")

    if not isinstance(output_template, str):
        raise AssertionError("yt-dlp output template is not configured")

    return Path(output_template).parent


def create_video_task(target_dir: Path) -> DownloadTask:
    return DownloadTask.create(
        url=MediaUrl("https://www.youtube.com/watch?v=test"),
        target_dir=target_dir,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
        include_playlist=False,
    )
