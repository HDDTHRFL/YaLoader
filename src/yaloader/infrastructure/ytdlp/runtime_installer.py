from __future__ import annotations

import json
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, cast
from uuid import uuid4

from yaloader.application.dto.ytdlp_runtime_update import (
    YtDlpRuntimeUpdateResult,
    build_ytdlp_runtime_update_progress,
)
from yaloader.application.ports.ytdlp_runtime_installer import (
    YtDlpRuntimeUpdateProgressCallback,
)
from yaloader.infrastructure.tools.archive_extraction import (
    ArchiveExtractionError,
    safe_extract_zip_archive,
)
from yaloader.infrastructure.tools.http_file_downloader import (
    FileDownloader,
    FileDownloadError,
    HttpFileDownloader,
)
from yaloader.infrastructure.ytdlp.runtime_manager import (
    YtDlpRuntimeManager,
    cleanup_failed_external_runtime_import,
    extract_ytdlp_module_version,
    has_external_ytdlp_runtime,
    load_ytdlp_module_from_path,
    remove_ytdlp_modules,
    validate_ytdlp_module,
)

YTDLP_PYPI_JSON_URL: Final = "https://pypi.org/pypi/yt-dlp/json"

VERSION_RESOLUTION_PERCENT: Final = 5
DOWNLOAD_START_PERCENT: Final = 10
DOWNLOAD_END_PERCENT: Final = 75
EXTRACTION_PERCENT: Final = 82
VALIDATION_PERCENT: Final = 88
INSTALLATION_PERCENT: Final = 94
COMPLETED_PERCENT: Final = 100

TEMPORARY_RUNTIME_DIR_NAME: Final = "_tmp"
STAGING_RUNTIME_DIR_NAME: Final = "current"
PREVIOUS_RUNTIME_DIR_NAME: Final = "previous"


class YtDlpRuntimeInstallationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class YtDlpWheelRelease:
    version: str
    filename: str
    url: str
    size_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class YtDlpWheelRuntimeInstaller:
    runtime_manager: YtDlpRuntimeManager
    downloader: FileDownloader = field(default_factory=HttpFileDownloader)

    def install_latest(
        self,
        progress_callback: YtDlpRuntimeUpdateProgressCallback | None = None,
    ) -> YtDlpRuntimeUpdateResult:
        temporary_root_dir = self._build_temporary_root_dir()
        staging_dir = temporary_root_dir / STAGING_RUNTIME_DIR_NAME

        try:
            self._emit_progress(
                progress_callback=progress_callback,
                message="Получаем актуальную версию yt-dlp",
                percent=VERSION_RESOLUTION_PERCENT,
            )
            release = self._resolve_latest_release()

            temporary_root_dir.mkdir(parents=True, exist_ok=True)
            wheel_file = temporary_root_dir / release.filename

            self._emit_progress(
                progress_callback=progress_callback,
                message=f"Скачиваем yt-dlp {release.version}",
                percent=DOWNLOAD_START_PERCENT,
            )
            self.downloader.download_file(
                url=release.url,
                destination_file=wheel_file,
                progress_callback=lambda downloaded_bytes, total_bytes: (
                    self._handle_download_progress(
                        downloaded_bytes=downloaded_bytes,
                        total_bytes=total_bytes,
                        progress_callback=progress_callback,
                    )
                ),
            )

            self._emit_progress(
                progress_callback=progress_callback,
                message="Распаковываем yt-dlp",
                percent=EXTRACTION_PERCENT,
            )
            safe_extract_zip_archive(
                archive_file=wheel_file,
                destination_dir=staging_dir,
            )

            self._emit_progress(
                progress_callback=progress_callback,
                message="Проверяем пользовательский yt-dlp",
                percent=VALIDATION_PERCENT,
            )
            validate_external_ytdlp_runtime(
                runtime_dir=staging_dir,
                expected_version=release.version,
            )

            self._emit_progress(
                progress_callback=progress_callback,
                message="Подключаем пользовательский yt-dlp",
                percent=INSTALLATION_PERCENT,
            )
            replace_current_runtime(
                runtime_manager=self.runtime_manager,
                staging_dir=staging_dir,
            )

            runtime_info = self.runtime_manager.get_runtime_info()

            if not runtime_info.is_external:
                raise YtDlpRuntimeInstallationError(
                    "после установки активным остался встроенный yt-dlp"
                )

            self._emit_progress(
                progress_callback=progress_callback,
                message=f"yt-dlp {runtime_info.version} подключён",
                percent=COMPLETED_PERCENT,
                path=runtime_info.path,
            )
            return YtDlpRuntimeUpdateResult.installed(runtime_info=runtime_info)
        except (
            OSError,
            ArchiveExtractionError,
            FileDownloadError,
            YtDlpRuntimeInstallationError,
        ) as error:
            return YtDlpRuntimeUpdateResult.failed(
                message=f"Не удалось обновить yt-dlp: {error}",
            )
        finally:
            remove_directory_if_exists(directory_path=temporary_root_dir)

    def _resolve_latest_release(self) -> YtDlpWheelRelease:
        payload = cast(object, json.loads(self.downloader.download_text(url=YTDLP_PYPI_JSON_URL)))
        return extract_latest_ytdlp_wheel_release(payload=payload)

    def _build_temporary_root_dir(self) -> Path:
        return (
            self.runtime_manager.runtime_dir / TEMPORARY_RUNTIME_DIR_NAME / f"yt-dlp-{uuid4().hex}"
        )

    def _handle_download_progress(
        self,
        *,
        downloaded_bytes: int,
        total_bytes: int | None,
        progress_callback: YtDlpRuntimeUpdateProgressCallback | None,
    ) -> None:
        if total_bytes is None or total_bytes <= 0:
            return

        download_range = DOWNLOAD_END_PERCENT - DOWNLOAD_START_PERCENT
        percent = DOWNLOAD_START_PERCENT + round(downloaded_bytes / total_bytes * download_range)
        bounded_percent = max(DOWNLOAD_START_PERCENT, min(DOWNLOAD_END_PERCENT, percent))

        self._emit_progress(
            progress_callback=progress_callback,
            message="Скачиваем yt-dlp",
            percent=bounded_percent,
        )

    def _emit_progress(
        self,
        *,
        progress_callback: YtDlpRuntimeUpdateProgressCallback | None,
        message: str,
        percent: int | None = None,
        path: Path | None = None,
    ) -> None:
        if progress_callback is None:
            return

        progress_callback(
            build_ytdlp_runtime_update_progress(
                message=message,
                percent=percent,
                path=path,
            )
        )


def extract_latest_ytdlp_wheel_release(*, payload: object) -> YtDlpWheelRelease:
    payload_mapping = ensure_mapping(value=payload, description="PyPI response")
    info_mapping = ensure_mapping(
        value=payload_mapping.get("info"),
        description="PyPI info",
    )
    version = get_required_string(mapping=info_mapping, key="version")
    urls = ensure_sequence(value=payload_mapping.get("urls"), description="PyPI urls")

    for item in urls:
        if not isinstance(item, Mapping):
            continue

        item_mapping = cast(Mapping[object, object], item)

        if item_mapping.get("packagetype") != "bdist_wheel":
            continue

        filename = get_required_string(mapping=item_mapping, key="filename")

        if not filename.endswith(".whl"):
            continue

        if "py3-none-any" not in filename:
            continue

        return YtDlpWheelRelease(
            version=version,
            filename=filename,
            url=get_required_string(mapping=item_mapping, key="url"),
            size_bytes=get_optional_int(mapping=item_mapping, key="size"),
        )

    raise YtDlpRuntimeInstallationError("PyPI не вернул подходящий wheel yt-dlp")


def validate_external_ytdlp_runtime(*, runtime_dir: Path, expected_version: str) -> None:
    if not has_external_ytdlp_runtime(runtime_dir=runtime_dir):
        raise YtDlpRuntimeInstallationError("wheel yt-dlp не содержит пакет yt_dlp")

    module = load_ytdlp_module_from_path(runtime_dir=runtime_dir)

    try:
        validate_ytdlp_module(module=module)
        actual_version = extract_ytdlp_module_version(module=module)
    finally:
        cleanup_failed_external_runtime_import(runtime_dir=runtime_dir)

    if actual_version != expected_version:
        raise YtDlpRuntimeInstallationError(
            "версия wheel не совпадает с PyPI: "
            f"ожидали {expected_version}, получили {actual_version}"
        )


def replace_current_runtime(*, runtime_manager: YtDlpRuntimeManager, staging_dir: Path) -> None:
    runtime_manager.runtime_dir.mkdir(parents=True, exist_ok=True)

    current_dir = runtime_manager.current_dir
    previous_dir = runtime_manager.runtime_dir / PREVIOUS_RUNTIME_DIR_NAME

    cleanup_failed_external_runtime_import(runtime_dir=current_dir)
    cleanup_failed_external_runtime_import(runtime_dir=staging_dir)
    remove_ytdlp_modules()
    remove_directory_if_exists(directory_path=previous_dir)

    if current_dir.exists():
        shutil.move(str(current_dir), str(previous_dir))

    try:
        shutil.move(str(staging_dir), str(current_dir))
    except OSError:
        if previous_dir.exists() and not current_dir.exists():
            shutil.move(str(previous_dir), str(current_dir))

        raise

    remove_directory_if_exists(directory_path=previous_dir)


def ensure_mapping(*, value: object, description: str) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise YtDlpRuntimeInstallationError(f"{description} имеет неожиданный формат")

    return cast(Mapping[object, object], value)


def ensure_sequence(*, value: object, description: str) -> Sequence[object]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise YtDlpRuntimeInstallationError(f"{description} имеет неожиданный формат")

    return cast(Sequence[object], value)


def get_required_string(*, mapping: Mapping[object, object], key: str) -> str:
    value = mapping.get(key)

    if not isinstance(value, str) or not value.strip():
        raise YtDlpRuntimeInstallationError(f"PyPI response не содержит поле {key}")

    return value.strip()


def get_optional_int(*, mapping: Mapping[object, object], key: str) -> int | None:
    value = mapping.get(key)

    if isinstance(value, int) and value > 0:
        return value

    return None


def remove_directory_if_exists(*, directory_path: Path) -> None:
    if directory_path.exists():
        shutil.rmtree(directory_path)
