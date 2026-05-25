from __future__ import annotations

from dataclasses import dataclass

from yaloader.config.paths import AppPaths, build_default_app_paths, ensure_app_directories


@dataclass(frozen=True, slots=True)
class AppContainer:
    paths: AppPaths


def build_app_container() -> AppContainer:
    paths = build_default_app_paths()
    ensure_app_directories(paths=paths)

    return AppContainer(paths=paths)
