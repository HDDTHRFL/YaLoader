from __future__ import annotations

import sys
from pathlib import Path

from yaloader.config.app_info import APP_NAME

APP_ICON_RELATIVE_PATH = Path("ui") / "assets" / "app_icon.ico"
TITLE_FONT_RELATIVE_PATH = Path("ui") / "assets" / "Death Stars.ttf"


def get_package_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)

    if isinstance(frozen_root, str):
        return Path(frozen_root) / APP_NAME

    return Path(__file__).resolve().parents[1]


def get_app_icon_path() -> Path:
    return get_package_root() / APP_ICON_RELATIVE_PATH


def get_title_font_path() -> Path:
    return get_package_root() / TITLE_FONT_RELATIVE_PATH
