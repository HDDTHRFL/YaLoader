from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from yaloader.infrastructure.tools import executable_version_resolver as resolver_module
from yaloader.infrastructure.tools.executable_version_resolver import (
    ToolExecutableVersionResolver,
)


def test_tool_executable_version_resolver_formats_deno_without_v_prefix(
    monkeypatch: MonkeyPatch,
) -> None:
    def fake_run_executable_for_text(
        *,
        executable_path: Path,
        args: tuple[str, ...],
    ) -> str:
        assert executable_path == Path("C:/Tools/deno.exe")
        assert args == ("--version",)

        return "deno 2.9.0\nv8 14.0.365.5\ntypescript 5.9.2"

    monkeypatch.setattr(
        resolver_module,
        "run_executable_for_text",
        fake_run_executable_for_text,
    )

    resolver = ToolExecutableVersionResolver()

    assert (
        resolver.resolve_version(
            executable_path=Path("C:/Tools/deno.exe"),
            executable_name="deno",
        )
        == "2.9.0"
    )


def test_tool_executable_version_resolver_keeps_ffmpeg_plain_version(
    monkeypatch: MonkeyPatch,
) -> None:
    def fake_run_executable_for_text(
        *,
        executable_path: Path,
        args: tuple[str, ...],
    ) -> str:
        assert executable_path == Path("C:/Tools/ffmpeg.exe")
        assert args == ("-version",)

        return "ffmpeg version 8.1.2-full_build-www.gyan.dev"

    monkeypatch.setattr(
        resolver_module,
        "run_executable_for_text",
        fake_run_executable_for_text,
    )

    resolver = ToolExecutableVersionResolver()

    assert (
        resolver.resolve_version(
            executable_path=Path("C:/Tools/ffmpeg.exe"),
            executable_name="ffmpeg",
        )
        == "8.1.2"
    )
