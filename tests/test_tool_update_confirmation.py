from __future__ import annotations

from pathlib import Path

from yaloader.application.dto.tool_installation import ToolId, ToolUpdateCheckResult
from yaloader.ui.tool_update_confirmation import build_tool_update_confirmation_text


def test_build_tool_update_confirmation_uses_update_button_when_updates_found() -> None:
    confirmation_text = build_tool_update_confirmation_text(
        update_checks=(
            ToolUpdateCheckResult.update_available(
                tool_id=ToolId.FFMPEG,
                current_version="7.0",
                latest_version="8.0",
                executable_path=Path("C:/Tools/ffmpeg.exe"),
            ),
            ToolUpdateCheckResult.up_to_date(
                tool_id=ToolId.DENO,
                current_version="2.0.0",
                latest_version="2.0.0",
                executable_path=Path("C:/Tools/deno.exe"),
            ),
        )
    )

    assert confirmation_text.title == "Обновить инструменты?"
    assert confirmation_text.confirm_button_text == "Обновить"
    assert confirmation_text.started_status_message == "Обновление инструментов запущено"
    assert "FFmpeg: 7.0 → 8.0" in confirmation_text.informative_text
    assert "Deno: актуальная версия 2.0.0" in confirmation_text.informative_text


def test_build_tool_update_confirmation_uses_reinstall_button_without_updates() -> None:
    confirmation_text = build_tool_update_confirmation_text(
        update_checks=(
            ToolUpdateCheckResult.up_to_date(
                tool_id=ToolId.FFMPEG,
                current_version="8.0",
                latest_version="8.0",
                executable_path=Path("C:/Tools/ffmpeg.exe"),
            ),
            ToolUpdateCheckResult.up_to_date(
                tool_id=ToolId.DENO,
                current_version="2.0.0",
                latest_version="2.0.0",
                executable_path=Path("C:/Tools/deno.exe"),
            ),
        )
    )

    assert confirmation_text.title == "Переустановить инструменты?"
    assert confirmation_text.confirm_button_text == "Переустановить"
    assert confirmation_text.started_status_message == "Переустановка инструментов запущена"
    assert "FFmpeg: актуальная версия 8.0" in confirmation_text.informative_text
    assert "Deno: актуальная версия 2.0.0" in confirmation_text.informative_text
