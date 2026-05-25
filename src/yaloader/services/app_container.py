from __future__ import annotations

from dataclasses import dataclass

from yaloader.application.ports.downloader import Downloader
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.config.paths import AppPaths, build_default_app_paths, ensure_app_directories
from yaloader.infrastructure.ytdlp.downloader import YtDlpDownloader


@dataclass(frozen=True, slots=True)
class AppContainer:
    paths: AppPaths
    download_queue_service: DownloadQueueService
    downloader: Downloader


def build_app_container() -> AppContainer:
    paths = build_default_app_paths()
    ensure_app_directories(paths=paths)

    return AppContainer(
        paths=paths,
        download_queue_service=DownloadQueueService(),
        downloader=YtDlpDownloader.create_default(),
    )
