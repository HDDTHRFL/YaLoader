from __future__ import annotations

from pathlib import Path

from yaloader.application.dto.tool_installation import ToolId, ToolUpdateCheckResult
from yaloader.ui.tool_update_dialog import (
    build_combined_tool_update_details,
    build_managed_tool_update_button_text,
    build_managed_tool_update_started_message,
    should_offer_ytdlp_update,
)


def test_build_managed_tool_update_button_text_uses_update_when_ffmpeg_update_exists() -> None:
    update_checks = (
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

    assert build_managed_tool_update_button_text(update_checks=update_checks) == ("Обновить FFmpeg/Deno")
    assert build_managed_tool_update_started_message(update_checks=update_checks) == ("Обновление FFmpeg/Deno запущено")


def test_build_managed_tool_update_button_text_uses_reinstall_without_updates() -> None:
    update_checks = (
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

    assert build_managed_tool_update_button_text(update_checks=update_checks) == ("Переустановить FFmpeg/Deno")
    assert build_managed_tool_update_started_message(update_checks=update_checks) == (
        "Переустановка FFmpeg/Deno запущена"
    )


def test_should_offer_ytdlp_update_only_when_ytdlp_update_is_available() -> None:
    assert (
        should_offer_ytdlp_update(
            update_check=ToolUpdateCheckResult.update_available(
                tool_id=ToolId.YTDLP,
                current_version="2026.3.17",
                latest_version="2026.6.9",
            )
        )
        is True
    )

    assert (
        should_offer_ytdlp_update(
            update_check=ToolUpdateCheckResult.up_to_date(
                tool_id=ToolId.YTDLP,
                current_version="2026.6.9",
                latest_version="2026.6.9",
            )
        )
        is False
    )


def test_build_combined_tool_update_details_contains_all_tools() -> None:
    details = build_combined_tool_update_details(
        managed_update_checks=(
            ToolUpdateCheckResult.up_to_date(
                tool_id=ToolId.FFMPEG,
                current_version="8.1.2",
                latest_version="8.1.2",
                executable_path=Path("C:/Tools/ffmpeg.exe"),
            ),
            ToolUpdateCheckResult.up_to_date(
                tool_id=ToolId.DENO,
                current_version="2.9.0",
                latest_version="2.9.0",
                executable_path=Path("C:/Tools/deno.exe"),
            ),
        ),
        ytdlp_update_check=ToolUpdateCheckResult.update_available(
            tool_id=ToolId.YTDLP,
            current_version="2026.3.17",
            latest_version="2026.6.9",
        ),
    )

    assert "FFmpeg: актуальная версия 8.1.2" in details
    assert "Deno: актуальная версия 2.9.0" in details
    assert "yt-dlp: 2026.3.17 → 2026.6.9" in details
    assert "Встроенная версия yt-dlp остаётся внутри приложения" in details
