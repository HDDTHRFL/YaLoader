from __future__ import annotations

from dataclasses import dataclass

from yaloader.application.dto.app_settings import AppSettings
from yaloader.application.ports.downloader import Downloader
from yaloader.application.services.download_history_service import DownloadHistoryService
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.application.services.environment_check_service import EnvironmentCheckService
from yaloader.application.services.settings_service import SettingsService
from yaloader.config.paths import AppPaths, build_default_app_paths, ensure_app_directories
from yaloader.infrastructure.system.process_runner import SystemProcessRunner
from yaloader.infrastructure.ytdlp.downloader import YtDlpDownloader


@dataclass(frozen=True, slots=True)
class AppContainer:
    paths: AppPaths
    settings: AppSettings
    settings_service: SettingsService
    environment_check_service: EnvironmentCheckService
    download_queue_service: DownloadQueueService
    download_history_service: DownloadHistoryService
    downloader: Downloader


def build_app_container() -> AppContainer:
    paths = build_default_app_paths()
    ensure_app_directories(paths=paths)

    settings_service = SettingsService(
        settings_file=paths.settings_file,
        default_downloads_dir=paths.downloads_dir,
    )
    settings = settings_service.load()
    settings.downloads_dir.mkdir(parents=True, exist_ok=True)

    return AppContainer(
        paths=paths,
        settings=settings,
        settings_service=settings_service,
        environment_check_service=EnvironmentCheckService(
            paths=paths,
            process_runner=SystemProcessRunner(),
        ),
        download_queue_service=DownloadQueueService(),
        download_history_service=DownloadHistoryService(history_file=paths.history_file),
        downloader=YtDlpDownloader.create_default(cookies_file=paths.cookies_file),
    )
