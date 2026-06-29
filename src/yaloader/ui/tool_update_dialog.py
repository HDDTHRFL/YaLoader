from __future__ import annotations

from enum import StrEnum
from typing import Final

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QPushButton, QWidget

from yaloader.application.dto.tool_installation import ToolId, ToolUpdateCheckResult
from yaloader.ui.widgets.common.confirmation_dialogs import CONFIRMATION_DIALOG_STYLE_SHEET

MANAGED_TOOL_IDS: Final[frozenset[ToolId]] = frozenset(
    {
        ToolId.FFMPEG,
        ToolId.DENO,
    }
)


class ToolUpdateDialogAction(StrEnum):
    MANAGED_TOOLS = "managed_tools"
    YTDLP = "ytdlp"
    CANCEL = "cancel"


def choose_tool_update_action(
    *,
    parent: QWidget,
    managed_update_checks: tuple[ToolUpdateCheckResult, ...],
    ytdlp_update_check: ToolUpdateCheckResult,
) -> ToolUpdateDialogAction:
    message_box = QMessageBox(parent)
    message_box.setWindowTitle("Обновить инструменты?")
    message_box.setIcon(QMessageBox.Icon.Information)
    message_box.setText("Результат проверки инструментов.")
    message_box.setInformativeText(
        build_combined_tool_update_details(
            managed_update_checks=managed_update_checks,
            ytdlp_update_check=ytdlp_update_check,
        )
    )
    message_box.setTextFormat(Qt.TextFormat.PlainText)
    message_box.setModal(True)
    message_box.setStyleSheet(CONFIRMATION_DIALOG_STYLE_SHEET)

    managed_button = QPushButton(
        build_managed_tool_update_button_text(update_checks=managed_update_checks),
        message_box,
    )
    managed_button.setObjectName("DialogSuccessButton")
    managed_button.setCursor(Qt.CursorShape.PointingHandCursor)

    ytdlp_button: QPushButton | None = None

    if should_offer_ytdlp_update(update_check=ytdlp_update_check):
        ytdlp_button = QPushButton("Обновить yt-dlp", message_box)
        ytdlp_button.setObjectName("DialogSuccessButton")
        ytdlp_button.setCursor(Qt.CursorShape.PointingHandCursor)

    cancel_button = QPushButton("Отмена", message_box)
    cancel_button.setObjectName("DialogSecondaryButton")
    cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)

    message_box.addButton(managed_button, QMessageBox.ButtonRole.AcceptRole)

    if ytdlp_button is not None:
        message_box.addButton(ytdlp_button, QMessageBox.ButtonRole.ActionRole)

    message_box.addButton(cancel_button, QMessageBox.ButtonRole.RejectRole)
    message_box.setDefaultButton(cancel_button)
    message_box.setEscapeButton(cancel_button)

    message_box.exec()
    clicked_button = message_box.clickedButton()

    if clicked_button == managed_button:
        return ToolUpdateDialogAction.MANAGED_TOOLS

    if ytdlp_button is not None and clicked_button == ytdlp_button:
        return ToolUpdateDialogAction.YTDLP

    return ToolUpdateDialogAction.CANCEL


def build_combined_tool_update_details(
    *,
    managed_update_checks: tuple[ToolUpdateCheckResult, ...],
    ytdlp_update_check: ToolUpdateCheckResult,
) -> str:
    lines = (
        *(
            format_tool_update_check_for_user(update_check=update_check)
            for update_check in managed_update_checks
        ),
        format_tool_update_check_for_user(update_check=ytdlp_update_check),
    )

    formatted_lines = "\n".join(f"- {line}" for line in lines)

    return (
        "Результат проверки:\n"
        f"{formatted_lines}\n\n"
        "FFmpeg и Deno устанавливаются как portable-инструменты YaLoader.\n"
        "yt-dlp обновляется отдельно как пользовательский runtime. "
        "Встроенная версия yt-dlp остаётся внутри приложения для аварийного отката."
    )


def build_managed_tool_update_button_text(
    *,
    update_checks: tuple[ToolUpdateCheckResult, ...],
) -> str:
    if has_managed_tool_updates(update_checks=update_checks):
        return "Обновить FFmpeg/Deno"

    return "Переустановить FFmpeg/Deno"


def build_managed_tool_update_started_message(
    *,
    update_checks: tuple[ToolUpdateCheckResult, ...],
) -> str:
    if has_managed_tool_updates(update_checks=update_checks):
        return "Обновление FFmpeg/Deno запущено"

    return "Переустановка FFmpeg/Deno запущена"


def has_managed_tool_updates(*, update_checks: tuple[ToolUpdateCheckResult, ...]) -> bool:
    return any(
        update_check.tool_id in MANAGED_TOOL_IDS and update_check.should_update
        for update_check in update_checks
    )


def should_offer_ytdlp_update(*, update_check: ToolUpdateCheckResult) -> bool:
    return update_check.tool_id is ToolId.YTDLP and update_check.should_update


def format_tool_update_check_for_user(*, update_check: ToolUpdateCheckResult) -> str:
    tool_name = format_tool_id_for_user(tool_id=update_check.tool_id)

    if update_check.should_update:
        if update_check.current_version is not None and update_check.latest_version is not None:
            return f"{tool_name}: {update_check.current_version} → {update_check.latest_version}"

        return f"{tool_name}: доступно обновление"

    if update_check.is_success:
        if update_check.current_version is not None:
            return f"{tool_name}: актуальная версия {update_check.current_version}"

        return f"{tool_name}: актуальная версия"

    return f"{tool_name}: {update_check.message}"


def format_tool_id_for_user(*, tool_id: ToolId) -> str:
    if tool_id is ToolId.FFMPEG:
        return "FFmpeg"

    if tool_id is ToolId.DENO:
        return "Deno"

    return "yt-dlp"
