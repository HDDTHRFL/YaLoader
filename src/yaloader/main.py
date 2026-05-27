from __future__ import annotations

from loguru import logger

from yaloader.config.logging_config import configure_application_logging
from yaloader.services.app_container import build_app_container
from yaloader.ui.application import run_gui_application


def main() -> None:
    container = build_app_container()
    configure_application_logging(paths=container.paths)

    logger.info(
        "Application container initialized. downloads_dir={} settings_file={} cookies_file={}",
        container.settings.downloads_dir,
        container.paths.settings_file,
        container.paths.cookies_file,
    )

    try:
        exit_code = run_gui_application(container=container)
    except Exception:
        logger.exception("Unhandled application error.")
        raise

    logger.info("Application stopped. exit_code={}", exit_code)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
