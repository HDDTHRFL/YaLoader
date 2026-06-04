from __future__ import annotations

from dataclasses import dataclass

from yaloader.application.dto.app_settings import AppSettings
from yaloader.application.ports.download_preparer import DownloadPreparer
from yaloader.application.ports.downloader import Downloader
from yaloader.application.services.download_history_service import DownloadHistoryService
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.application.services.download_speed_limit_state import DownloadSpeedLimitState
from yaloader.application.services.environment_check_service import EnvironmentCheckService
from yaloader.application.services.media_metadata_service import MediaMetadataService
from yaloader.application.services.prepared_download_cache import PreparedDownloadCache
from yaloader.application.services.settings_service import SettingsService
from yaloader.config.paths import AppPaths, build_default_app_paths, ensure_app_directories
from yaloader.infrastructure.system.process_runner import SystemProcessRunner
from yaloader.infrastructure.ytdlp.download_preparer import YtDlpDownloadPreparer
from yaloader.infrastructure.ytdlp.downloader import YtDlpDownloader
from yaloader.infrastructure.ytdlp.metadata_extractor import YtDlpMetadataExtractor


@dataclass(frozen=True, slots=True)
class AppContainer:
    paths: AppPaths
    settings: AppSettings
    settings_service: SettingsService
    environment_check_service: EnvironmentCheckService
    download_queue_service: DownloadQueueService
    download_speed_limit_state: DownloadSpeedLimitState
    download_history_service: DownloadHistoryService
    prepared_download_cache: PreparedDownloadCache
    media_metadata_service: MediaMetadataService
    download_preparer: DownloadPreparer
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
    download_speed_limit_state = DownloadSpeedLimitState(
        bytes_per_second=settings.download_speed_limit_bytes_per_second,
    )

    return AppContainer(
        paths=paths,
        settings=settings,
        settings_service=settings_service,
        environment_check_service=EnvironmentCheckService(
            paths=paths,
            process_runner=SystemProcessRunner(),
        ),
        download_queue_service=DownloadQueueService(),
        download_speed_limit_state=download_speed_limit_state,
        download_history_service=DownloadHistoryService(history_file=paths.history_file),
        prepared_download_cache=PreparedDownloadCache(),
        media_metadata_service=MediaMetadataService(
            extractor=YtDlpMetadataExtractor.create_default(cookies_file=paths.cookies_file),
        ),
        download_preparer=YtDlpDownloadPreparer.create_default(
            cookies_file=paths.cookies_file,
        ),
        downloader=YtDlpDownloader.create_default(
            cookies_file=paths.cookies_file,
            speed_limit_provider=download_speed_limit_state,
        ),
    )
