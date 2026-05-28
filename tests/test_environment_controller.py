from __future__ import annotations

from pathlib import Path

from yaloader.application.services.environment_check_service import EnvironmentCheckService
from yaloader.application.services.settings_service import SettingsService
from yaloader.config.paths import AppPaths
from yaloader.ui.controllers.environment_controller import EnvironmentController


class FakeProcessRunner:
    def __init__(self, executables: dict[str, Path]) -> None:
        self._executables = executables

    def find_executable(self, executable_name: str) -> Path | None:
        return self._executables.get(executable_name)


def test_load_status_returns_environment_status(tmp_path: Path) -> None:
    controller = create_controller(tmp_path=tmp_path)
    downloads_dir = tmp_path / "downloads"

    update = controller.load_status(downloads_dir=downloads_dir)

    assert update.environment_status is not None
    assert update.environment_status.downloads_dir.is_ok is True
    assert update.status_message is None
    assert update.should_play_refresh_feedback is False


def test_refresh_status_requests_feedback_and_returns_status(tmp_path: Path) -> None:
    controller = create_controller(tmp_path=tmp_path)
    downloads_dir = tmp_path / "downloads"

    update = controller.refresh_status(downloads_dir=downloads_dir)

    assert update.environment_status is not None
    assert update.status_message == "Состояние системы обновлено"
    assert update.should_play_refresh_feedback is True


def test_change_downloads_dir_saves_settings_and_returns_status(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)
    controller = create_controller(tmp_path=tmp_path, paths=paths)
    downloads_dir = tmp_path / "custom_downloads"

    update = controller.change_downloads_dir(downloads_dir=downloads_dir)

    assert update.settings is not None
    assert update.settings.downloads_dir == downloads_dir
    assert update.environment_status is not None
    assert update.environment_status.downloads_dir.is_ok is True
    assert update.status_message == f"Папка загрузок изменена: {downloads_dir}"
    assert paths.settings_file.is_file() is True


def test_change_downloads_dir_rejects_relative_path(tmp_path: Path) -> None:
    controller = create_controller(tmp_path=tmp_path)

    update = controller.change_downloads_dir(downloads_dir=Path("downloads"))

    assert update.settings is None
    assert update.environment_status is None
    assert update.status_message == "Папка загрузок должна быть абсолютным путём"


def test_delete_cookies_removes_existing_file_and_refreshes_status(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)
    paths.cookies_file.write_text(
        "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tTEST\tVALUE\n",
        encoding="utf-8",
    )
    controller = create_controller(tmp_path=tmp_path, paths=paths)

    update = controller.delete_cookies(downloads_dir=paths.downloads_dir)

    assert paths.cookies_file.is_file() is False
    assert update.environment_status is not None
    assert update.environment_status.cookies.is_ok is False
    assert update.status_message == f"cookies.txt удалён безвозвратно: {paths.cookies_file}"


def test_delete_cookies_reports_missing_file_and_refreshes_status(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)
    controller = create_controller(tmp_path=tmp_path, paths=paths)

    update = controller.delete_cookies(downloads_dir=paths.downloads_dir)

    assert update.environment_status is not None
    assert update.environment_status.cookies.is_ok is False
    assert update.status_message == f"cookies.txt не найден: {paths.cookies_file}"


def test_open_cookies_dir_creates_data_dir_and_returns_directory(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)
    paths.data_dir.rmdir()
    controller = create_controller(tmp_path=tmp_path, paths=paths)

    update = controller.open_cookies_dir()

    assert paths.data_dir.is_dir() is True
    assert update.directory_to_open == paths.data_dir
    assert update.status_message is None


def test_open_downloads_dir_creates_directory_and_returns_directory(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)
    downloads_dir = tmp_path / "custom_downloads"
    controller = create_controller(tmp_path=tmp_path, paths=paths)

    update = controller.open_downloads_dir(downloads_dir=downloads_dir)

    assert downloads_dir.is_dir() is True
    assert update.directory_to_open == downloads_dir
    assert update.status_message is None


def create_controller(
    *,
    tmp_path: Path,
    paths: AppPaths | None = None,
) -> EnvironmentController:
    app_paths = paths if paths is not None else create_app_paths(tmp_path=tmp_path)

    return EnvironmentController(
        paths=app_paths,
        settings_service=SettingsService(
            settings_file=app_paths.settings_file,
            default_downloads_dir=app_paths.downloads_dir,
        ),
        environment_check_service=EnvironmentCheckService(
            paths=app_paths,
            process_runner=FakeProcessRunner(
                executables={
                    "ffmpeg": Path("C:/Tools/ffmpeg.exe"),
                    "deno": Path("C:/Tools/deno.exe"),
                }
            ),
        ),
    )


def create_app_paths(tmp_path: Path) -> AppPaths:
    data_dir = tmp_path / "appdata"
    data_dir.mkdir(parents=True, exist_ok=True)

    return AppPaths(
        data_dir=data_dir,
        downloads_dir=tmp_path / "downloads",
        logs_dir=data_dir / "logs",
        settings_file=data_dir / "settings.json",
        cookies_file=data_dir / "cookies.txt",
        history_file=data_dir / "download_history.json",
    )
