from __future__ import annotations

from pathlib import Path

from yaloader.application.services.environment_check_service import EnvironmentCheckService
from yaloader.config.paths import AppPaths


class FakeProcessRunner:
    def __init__(self, executables: dict[str, Path]) -> None:
        self._executables = executables

    def find_executable(self, executable_name: str) -> Path | None:
        return self._executables.get(executable_name)


def test_environment_check_reports_missing_external_tools(tmp_path: Path) -> None:
    service = EnvironmentCheckService(
        paths=create_app_paths(tmp_path=tmp_path),
        process_runner=FakeProcessRunner(executables={}),
    )

    status = service.check(downloads_dir=tmp_path / "downloads")

    assert status.ffmpeg.is_ok is False
    assert status.deno.is_ok is False
    assert status.ytdlp.is_ok is True
    assert status.cookies.is_ok is False
    assert status.downloads_dir.is_ok is True


def test_environment_check_accepts_valid_cookies_file(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)
    paths.cookies_file.write_text(
        "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tTEST\tVALUE\n",
        encoding="utf-8",
    )
    service = EnvironmentCheckService(
        paths=paths,
        process_runner=FakeProcessRunner(
            executables={
                "ffmpeg": Path("C:/Tools/ffmpeg.exe"),
                "deno": Path("C:/Tools/deno.exe"),
            }
        ),
    )

    status = service.check(downloads_dir=tmp_path / "downloads")

    assert status.ffmpeg.is_ok is True
    assert status.deno.is_ok is True
    assert status.cookies.is_ok is True
    assert status.downloads_dir.is_ok is True


def test_environment_check_rejects_suspicious_cookies_file(tmp_path: Path) -> None:
    paths = create_app_paths(tmp_path=tmp_path)
    paths.cookies_file.write_text("not a netscape cookies file\n", encoding="utf-8")
    service = EnvironmentCheckService(
        paths=paths,
        process_runner=FakeProcessRunner(executables={}),
    )

    status = service.check(downloads_dir=tmp_path / "downloads")

    assert status.cookies.is_ok is False
    assert "подозрительный формат" in status.cookies.message


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
