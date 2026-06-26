from __future__ import annotations

from dataclasses import dataclass

from yaloader.application.dto.app_settings import AppSettings
from yaloader.application.dto.tool_installation import ToolId
from yaloader.application.ports.download_preparer import DownloadPreparer
from yaloader.application.ports.downloader import Downloader
from yaloader.application.ports.platform_icon_resolver import PlatformIconResolver
from yaloader.application.services.browser_cookies_service import BrowserCookiesService
from yaloader.application.services.download_history_service import DownloadHistoryService
from yaloader.application.services.download_queue_service import DownloadQueueService
from yaloader.application.services.download_speed_limit_state import DownloadSpeedLimitState
from yaloader.application.services.environment_check_service import EnvironmentCheckService
from yaloader.application.services.media_metadata_service import MediaMetadataService
from yaloader.application.services.prepared_download_cache import PreparedDownloadCache
from yaloader.application.services.settings_service import SettingsService
from yaloader.application.services.tool_installation_service import ToolInstallationService
from yaloader.config.paths import AppPaths, build_default_app_paths, ensure_app_directories
from yaloader.infrastructure.system.tool_locator import ToolLocatorProcessRunner
from yaloader.infrastructure.tools.deno_installer import DenoPortableInstaller
from yaloader.infrastructure.tools.ffmpeg_installer import FfmpegPortableInstaller
from yaloader.infrastructure.web.favicon_resolver import WebFaviconResolver
from yaloader.infrastructure.ytdlp.browser_cookies_exporter import YtDlpBrowserCookiesExporter
from yaloader.infrastructure.ytdlp.download_preparer import YtDlpDownloadPreparer
from yaloader.infrastructure.ytdlp.downloader import YtDlpDownloader
from yaloader.infrastructure.ytdlp.metadata_extractor import YtDlpMetadataExtractor
from yaloader.infrastructure.ytdlp.version_checker import YtDlpPackageVersionChecker


@dataclass(frozen=True, slots=True)
class AppContainer:
    paths: AppPaths
    settings: AppSettings
    settings_service: SettingsService
    environment_check_service: EnvironmentCheckService
    browser_cookies_service: BrowserCookiesService
    tool_installation_service: ToolInstallationService
    download_queue_service: DownloadQueueService
    download_speed_limit_state: DownloadSpeedLimitState
    download_history_service: DownloadHistoryService
    prepared_download_cache: PreparedDownloadCache
    platform_icon_resolver: PlatformIconResolver
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
    prepared_download_cache = PreparedDownloadCache()
    tool_locator = ToolLocatorProcessRunner(paths=paths)

    return AppContainer(
        paths=paths,
        settings=settings,
        settings_service=settings_service,
        environment_check_service=EnvironmentCheckService(
            paths=paths,
            process_runner=tool_locator,
        ),
        browser_cookies_service=BrowserCookiesService(
            exporter=YtDlpBrowserCookiesExporter(),
            target_file=paths.cookies_file,
        ),
        tool_installation_service=ToolInstallationService(
            process_runner=tool_locator,
            installers={
                ToolId.FFMPEG: FfmpegPortableInstaller(paths=paths),
                ToolId.DENO: DenoPortableInstaller(paths=paths),
            },
            version_checkers={
                ToolId.YTDLP: YtDlpPackageVersionChecker(),
            },
        ),
        download_queue_service=DownloadQueueService(),
        download_speed_limit_state=download_speed_limit_state,
        download_history_service=DownloadHistoryService(history_file=paths.history_file),
        prepared_download_cache=prepared_download_cache,
        platform_icon_resolver=WebFaviconResolver(
            cache_dir=paths.platform_icons_cache_dir,
        ),
        media_metadata_service=MediaMetadataService(
            extractor=YtDlpMetadataExtractor.create_default(
                cookies_file=paths.cookies_file,
                process_runner=tool_locator,
            ),
        ),
        download_preparer=YtDlpDownloadPreparer.create_default(
            cookies_file=paths.cookies_file,
            process_runner=tool_locator,
        ),
        downloader=YtDlpDownloader.create_default(
            cookies_file=paths.cookies_file,
            speed_limit_provider=download_speed_limit_state,
            prepared_download_cache=prepared_download_cache,
            process_runner=tool_locator,
        ),
    )
