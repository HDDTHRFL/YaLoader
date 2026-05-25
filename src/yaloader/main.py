from __future__ import annotations

from yaloader.services.app_container import build_app_container
from yaloader.ui.application import run_gui_application


def main() -> None:
    container = build_app_container()
    raise SystemExit(run_gui_application(container=container))


if __name__ == "__main__":
    main()
