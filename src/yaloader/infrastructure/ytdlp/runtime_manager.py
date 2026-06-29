from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Final

from loguru import logger

from yaloader.application.dto.ytdlp_runtime import YtDlpRuntimeInfo

YTDLP_DISTRIBUTION_NAME: Final = "yt-dlp"
YTDLP_IMPORT_NAME: Final = "yt_dlp"
YTDLP_RUNTIME_CURRENT_DIR_NAME: Final = "current"
YTDLP_RUNTIME_SCOPE_HASH_LENGTH: Final = 16


class YtDlpRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class YtDlpRuntimeManager:
    runtime_root_dir: Path

    @property
    def runtime_scope_id(self) -> str:
        return build_ytdlp_runtime_scope_id()

    @property
    def runtime_dir(self) -> Path:
        return self.runtime_root_dir / self.runtime_scope_id

    @property
    def current_dir(self) -> Path:
        return self.runtime_dir / YTDLP_RUNTIME_CURRENT_DIR_NAME

    def get_runtime_info(self) -> YtDlpRuntimeInfo:
        if has_external_ytdlp_runtime(runtime_dir=self.current_dir):
            try:
                module = self._load_external_module()
                version = extract_ytdlp_module_version(module=module)
                validate_ytdlp_module(module=module)

                return YtDlpRuntimeInfo.external(
                    version=version,
                    path=self.current_dir,
                )
            except Exception as error:
                logger.warning(
                    "External yt-dlp runtime is invalid. path={} error={}",
                    self.current_dir,
                    error,
                )
                cleanup_failed_external_runtime_import(runtime_dir=self.current_dir)

                return YtDlpRuntimeInfo.bundled(
                    version=get_bundled_ytdlp_version(),
                    fallback_reason=f"внешний yt-dlp отключён: {error}",
                )

        return YtDlpRuntimeInfo.bundled(version=get_bundled_ytdlp_version())

    def load_module(self) -> ModuleType:
        runtime_info = self.get_runtime_info()

        if runtime_info.is_external:
            return importlib.import_module(YTDLP_IMPORT_NAME)

        return load_bundled_ytdlp_module()

    def reset_external_runtime(self) -> bool:
        if not self.runtime_dir.exists():
            cleanup_failed_external_runtime_import(runtime_dir=self.current_dir)
            return False

        cleanup_failed_external_runtime_import(runtime_dir=self.current_dir)
        shutil.rmtree(self.runtime_dir)

        return True

    def _load_external_module(self) -> ModuleType:
        return load_ytdlp_module_from_path(runtime_dir=self.current_dir)


def load_ytdlp_module_from_path(*, runtime_dir: Path) -> ModuleType:
    runtime_dir_text = str(runtime_dir.resolve())
    remove_ytdlp_modules()
    ensure_first_sys_path_entry(path_text=runtime_dir_text)

    try:
        return importlib.import_module(YTDLP_IMPORT_NAME)
    except Exception:
        remove_sys_path_entry(path_text=runtime_dir_text)
        remove_ytdlp_modules()
        raise


def build_ytdlp_runtime_scope_id(*, executable_path: Path | None = None) -> str:
    source_path = Path(sys.executable) if executable_path is None else executable_path

    try:
        normalized_path = str(source_path.resolve()).casefold()
    except OSError:
        normalized_path = str(source_path.absolute()).casefold()

    digest = hashlib.sha256(normalized_path.encode("utf-8")).hexdigest()

    return digest[:YTDLP_RUNTIME_SCOPE_HASH_LENGTH]


def has_external_ytdlp_runtime(*, runtime_dir: Path) -> bool:
    return (runtime_dir / YTDLP_IMPORT_NAME / "__init__.py").is_file()


def get_bundled_ytdlp_version() -> str:
    try:
        return importlib.metadata.version(YTDLP_DISTRIBUTION_NAME)
    except importlib.metadata.PackageNotFoundError as error:
        raise YtDlpRuntimeError("встроенный yt-dlp не найден") from error


def load_bundled_ytdlp_module() -> ModuleType:
    remove_external_runtime_paths_from_sys_path()
    remove_ytdlp_modules()

    return importlib.import_module(YTDLP_IMPORT_NAME)


def extract_ytdlp_module_version(*, module: ModuleType) -> str:
    version_module = getattr(module, "version", None)
    version = getattr(version_module, "__version__", None)

    if isinstance(version, str) and version.strip():
        return version.strip()

    direct_version = getattr(module, "__version__", None)

    if isinstance(direct_version, str) and direct_version.strip():
        return direct_version.strip()

    return get_bundled_ytdlp_version()


def validate_ytdlp_module(*, module: ModuleType) -> None:
    youtube_dl_factory = getattr(module, "YoutubeDL", None)

    if not callable(youtube_dl_factory):
        raise YtDlpRuntimeError("модуль yt_dlp не содержит callable YoutubeDL")


def cleanup_failed_external_runtime_import(*, runtime_dir: Path) -> None:
    remove_sys_path_entry(path_text=str(runtime_dir.resolve()))
    remove_ytdlp_modules()


def ensure_first_sys_path_entry(*, path_text: str) -> None:
    remove_sys_path_entry(path_text=path_text)
    sys.path.insert(0, path_text)


def remove_sys_path_entry(*, path_text: str) -> None:
    normalized_path = normalize_sys_path_entry(value=path_text)
    sys.path[:] = [
        entry for entry in sys.path if normalize_sys_path_entry(value=entry) != normalized_path
    ]


def remove_external_runtime_paths_from_sys_path() -> None:
    sys.path[:] = [
        entry
        for entry in sys.path
        if YTDLP_RUNTIME_CURRENT_DIR_NAME not in normalize_sys_path_entry(value=entry)
    ]


def normalize_sys_path_entry(*, value: str) -> str:
    try:
        return str(Path(value).resolve()).casefold()
    except OSError:
        return value.strip().casefold()


def remove_ytdlp_modules() -> None:
    for module_name in tuple(sys.modules):
        if module_name == YTDLP_IMPORT_NAME or module_name.startswith(f"{YTDLP_IMPORT_NAME}."):
            del sys.modules[module_name]
