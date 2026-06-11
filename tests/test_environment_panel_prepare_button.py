from __future__ import annotations

from pathlib import Path

from yaloader.application.dto.environment_status import EnvironmentItemStatus, EnvironmentStatus
from yaloader.ui.widgets.environment_panel import (
    build_missing_required_tool_names,
    build_prepare_system_button_tooltip,
    should_show_prepare_system_button,
)


def test_should_show_prepare_system_button_when_ffmpeg_is_missing() -> None:
    status = build_environment_status(ffmpeg_ok=False, deno_ok=True)

    assert should_show_prepare_system_button(status=status) is True
    assert build_missing_required_tool_names(status=status) == ("FFmpeg",)


def test_should_show_prepare_system_button_when_deno_is_missing() -> None:
    status = build_environment_status(ffmpeg_ok=True, deno_ok=False)

    assert should_show_prepare_system_button(status=status) is True
    assert build_missing_required_tool_names(status=status) == ("Deno",)


def test_should_hide_prepare_system_button_when_required_tools_are_available() -> None:
    status = build_environment_status(ffmpeg_ok=True, deno_ok=True)

    assert should_show_prepare_system_button(status=status) is False
    assert build_missing_required_tool_names(status=status) == ()
    assert (
        build_prepare_system_button_tooltip(status=status)
        == "FFmpeg и Deno уже доступны. Для замены используйте «Обновить инструменты»."
    )


def build_environment_status(*, ffmpeg_ok: bool, deno_ok: bool) -> EnvironmentStatus:
    return EnvironmentStatus(
        ffmpeg=build_item_status(title="FFmpeg", is_ok=ffmpeg_ok),
        deno=build_item_status(title="Deno", is_ok=deno_ok),
        ytdlp=build_item_status(title="yt-dlp", is_ok=True),
        cookies=build_item_status(title="cookies.txt", is_ok=True),
        downloads_dir=build_item_status(title="Папка загрузок", is_ok=True),
    )


def build_item_status(*, title: str, is_ok: bool) -> EnvironmentItemStatus:
    return EnvironmentItemStatus(
        title=title,
        is_ok=is_ok,
        message="найден" if is_ok else "не найден",
        path=Path("C:/Tools/tool.exe") if is_ok else None,
    )
