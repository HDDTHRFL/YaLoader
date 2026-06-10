from __future__ import annotations

import os
from pathlib import Path

import pytest

from yaloader.infrastructure.ytdlp.runtime_environment import (
    YtDlpRuntimeEnvironment,
    build_extended_path,
    collect_ytdlp_runtime_executable_dirs,
)


class FakeExecutableLocator:
    def __init__(self, executable_paths: dict[str, Path]) -> None:
        self._executable_paths = executable_paths

    def find_executable(self, executable_name: str) -> Path | None:
        return self._executable_paths.get(executable_name)


def test_collect_ytdlp_runtime_executable_dirs_returns_unique_parent_dirs(
    tmp_path: Path,
) -> None:
    tools_dir = tmp_path / "tools"
    deno_dir = tools_dir / "deno"
    ffmpeg_bin_dir = tools_dir / "ffmpeg" / "bin"
    deno_executable = deno_dir / "deno.exe"
    ffmpeg_executable = ffmpeg_bin_dir / "ffmpeg.exe"

    deno_dir.mkdir(parents=True)
    ffmpeg_bin_dir.mkdir(parents=True)
    deno_executable.write_text("", encoding="utf-8")
    ffmpeg_executable.write_text("", encoding="utf-8")

    locator = FakeExecutableLocator(
        {
            "deno": deno_executable,
            "ffmpeg": ffmpeg_executable,
        }
    )

    executable_dirs = collect_ytdlp_runtime_executable_dirs(process_runner=locator)

    assert executable_dirs == (deno_dir, ffmpeg_bin_dir)


def test_build_extended_path_prepends_runtime_dirs_without_duplicates(
    tmp_path: Path,
) -> None:
    deno_dir = tmp_path / "deno"
    ffmpeg_dir = tmp_path / "ffmpeg" / "bin"
    deno_dir.mkdir(parents=True)
    ffmpeg_dir.mkdir(parents=True)

    previous_path = os.pathsep.join((str(deno_dir), "C:\\Windows\\System32"))

    extended_path = build_extended_path(
        executable_dirs=(deno_dir, ffmpeg_dir),
        previous_path=previous_path,
    )

    path_parts = extended_path.split(os.pathsep)

    assert path_parts[0] == str(deno_dir.resolve())
    assert path_parts[1] == str(ffmpeg_dir.resolve())
    assert path_parts.count(str(deno_dir.resolve())) == 1
    assert path_parts.count(str(ffmpeg_dir.resolve())) == 1


def test_ytdlp_runtime_environment_temporarily_extends_and_restores_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous_path = "C:\\Windows\\System32"
    deno_dir = tmp_path / "deno"
    deno_executable = deno_dir / "deno.exe"
    deno_dir.mkdir(parents=True)
    deno_executable.write_text("", encoding="utf-8")
    monkeypatch.setenv("PATH", previous_path)

    locator = FakeExecutableLocator({"deno": deno_executable})
    runtime_environment = YtDlpRuntimeEnvironment(process_runner=locator)

    with runtime_environment.apply():
        path_parts = os.environ["PATH"].split(os.pathsep)
        assert path_parts[0] == str(deno_dir.resolve())

    assert os.environ["PATH"] == previous_path
