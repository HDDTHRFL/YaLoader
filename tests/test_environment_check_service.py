from __future__ import annotations

from pathlib import Path

from yaloader.application.dto.ytdlp_runtime import YtDlpRuntimeInfo
from yaloader.application.services.environment_check_service import EnvironmentCheckService
from yaloader.config.paths import AppPaths


class FakeYtDlpRuntimeInfoProvider:
    def __init__(self, runtime_info: YtDlpRuntimeInfo) -> None:
        self._runtime_info = runtime_info

    def get_runtime_info(self) -> YtDlpRuntimeInfo:
        return self._runtime_info


class FakeProcessRunner:
    def __init__(self, executables: dict[str, Path]) -> None:
        self._executables = executables

    def find_executable(self, executable_name: str) -> Path | None:
        return self._executables.get(executable_name)


class FakeExecutableVersionResolver:
    def __init__(self, versions: dict[str, str]) -> None:
        self._versions = versions

    def resolve_version(
        self,
        *,
        executable_path: Path,
        executable_name: str,
    ) -> str:
        _ = executable_path
        return self._versions[executable_name]


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


def test_environment_check_reports_external_ytdlp_runtime(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    service = EnvironmentCheckService(
        paths=create_app_paths(tmp_path=tmp_path),
        process_runner=FakeProcessRunner(executables={}),
        ytdlp_runtime_provider=FakeYtDlpRuntimeInfoProvider(
            runtime_info=YtDlpRuntimeInfo.external(
                version="2026.4.1",
                path=runtime_dir,
            ),
        ),
    )

    status = service.check(downloads_dir=tmp_path / "downloads")

    assert status.ytdlp.is_ok is True
    assert status.ytdlp.message == "2026.4.1 (пользовательский)"
    assert status.ytdlp.path == runtime_dir


def test_environment_check_reports_disabled_external_ytdlp_runtime(tmp_path: Path) -> None:
    service = EnvironmentCheckService(
        paths=create_app_paths(tmp_path=tmp_path),
        process_runner=FakeProcessRunner(executables={}),
        ytdlp_runtime_provider=FakeYtDlpRuntimeInfoProvider(
            runtime_info=YtDlpRuntimeInfo.bundled(
                version="2026.3.17",
                fallback_reason="внешний yt-dlp отключён: broken",
            ),
        ),
    )

    status = service.check(downloads_dir=tmp_path / "downloads")

    assert status.ytdlp.is_ok is True
    assert status.ytdlp.message == "2026.3.17 (встроенный | внешний отключён)"


def test_environment_check_reports_ffmpeg_and_deno_versions(tmp_path: Path) -> None:
    service = EnvironmentCheckService(
        paths=create_app_paths(tmp_path=tmp_path),
        process_runner=FakeProcessRunner(
            executables={
                "ffmpeg": Path("C:/Tools/ffmpeg.exe"),
                "deno": Path("C:/Tools/deno.exe"),
            }
        ),
        executable_version_resolver=FakeExecutableVersionResolver(
            versions={
                "ffmpeg": "8.1.2",
                "deno": "2.9.0",
            }
        ),
    )

    status = service.check(downloads_dir=tmp_path / "downloads")

    assert status.ffmpeg.message == "8.1.2"
    assert status.deno.message == "2.9.0"
