from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final

from PyQt6.QtGui import QIcon

from yaloader.config.resources import get_platform_icon_path
from yaloader.domain.source_platform import SourcePlatform

PLATFORM_ICON_FILE_NAMES: Final[Mapping[SourcePlatform, str]] = {
    SourcePlatform.YOUTUBE: "youtube.png",
    SourcePlatform.RUTUBE: "rutube.png",
    SourcePlatform.VK_VIDEO: "vkvideo.png",
}


def build_source_platform_icon(*, platform: SourcePlatform) -> QIcon:
    icon_path = get_source_platform_icon_path(platform=platform)

    if icon_path is None or not icon_path.is_file():
        return QIcon()

    return QIcon(str(icon_path))


def get_source_platform_icon_path(*, platform: SourcePlatform) -> Path | None:
    file_name = PLATFORM_ICON_FILE_NAMES.get(platform)

    if file_name is None:
        return None

    return get_platform_icon_path(file_name=file_name)
