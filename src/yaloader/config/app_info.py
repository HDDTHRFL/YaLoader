from __future__ import annotations

import importlib.metadata
from typing import Final

APP_NAME: Final = "yaloader"
APP_DISPLAY_NAME: Final = "YaLoader"
ORGANIZATION_NAME: Final = "YaLoader"
UNKNOWN_APP_VERSION: Final = "0.0.0+unknown"


def resolve_application_version(*, package_name: str = APP_NAME) -> str:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return UNKNOWN_APP_VERSION


APP_VERSION: Final = resolve_application_version()
