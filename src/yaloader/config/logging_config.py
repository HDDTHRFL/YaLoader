from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from yaloader.config.app_info import APP_DISPLAY_NAME, APP_VERSION
from yaloader.config.paths import AppPaths

LOG_FILE_NAME = "yaloader.log"
LOG_ROTATION = "5 MB"
LOG_RETENTION = "14 days"
LOG_ENCODING = "utf-8"
LOG_LEVEL = "DEBUG"
CONSOLE_LOG_LEVEL = "INFO"

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "{process.id} | "
    "{thread.name} | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


def configure_application_logging(*, paths: AppPaths) -> Path:
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = paths.logs_dir / LOG_FILE_NAME

    logger.remove()
    logger.add(
        sys.stderr,
        level=CONSOLE_LOG_LEVEL,
        format=LOG_FORMAT,
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )
    logger.add(
        log_file_path,
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        encoding=LOG_ENCODING,
        backtrace=True,
        diagnose=False,
        enqueue=True,
    )

    logger.info("=" * 90)
    logger.info("{} started. version={}", APP_DISPLAY_NAME, APP_VERSION)
    logger.info("Log file: {}", log_file_path)
    logger.info("Data directory: {}", paths.data_dir)
    logger.info("Settings file: {}", paths.settings_file)
    logger.info("Cookies file: {}", paths.cookies_file)
    logger.info("Default downloads directory: {}", paths.downloads_dir)

    return log_file_path
