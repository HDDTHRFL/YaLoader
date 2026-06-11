from __future__ import annotations

from dataclasses import dataclass

from yaloader.application.dto.tool_installation import ToolId, ToolUpdateCheckResult

UPDATE_TOOLS_CONFIRMATION_BUTTON = "Обновить"
REINSTALL_TOOLS_CONFIRMATION_BUTTON = "Переустановить"

UPDATE_TOOLS_CONFIRMATION_TITLE = "Обновить инструменты?"
REINSTALL_TOOLS_CONFIRMATION_TITLE = "Переустановить инструменты?"

UPDATE_TOOLS_CONFIRMATION_TEXT = "Найдены новые версии инструментов."
REINSTALL_TOOLS_CONFIRMATION_TEXT = "Новых версий не найдено, но инструменты можно переустановить."

UPDATE_TOOLS_CANCELED_STATUS_MESSAGE = "Обновление инструментов отменено"
REINSTALL_TOOLS_CANCELED_STATUS_MESSAGE = "Переустановка инструментов отменена"

UPDATE_TOOLS_STARTED_STATUS_MESSAGE = "Обновление инструментов запущено"
REINSTALL_TOOLS_STARTED_STATUS_MESSAGE = "Переустановка инструментов запущена"


@dataclass(frozen=True, slots=True)
class ToolUpdateConfirmationText:
    title: str
    text: str
    informative_text: str
    confirm_button_text: str
    canceled_status_message: str
    started_status_message: str


def build_tool_update_confirmation_text(
    *,
    update_checks: tuple[ToolUpdateCheckResult, ...],
) -> ToolUpdateConfirmationText:
    if has_available_tool_updates(update_checks=update_checks):
        return ToolUpdateConfirmationText(
            title=UPDATE_TOOLS_CONFIRMATION_TITLE,
            text=UPDATE_TOOLS_CONFIRMATION_TEXT,
            informative_text=build_tool_update_confirmation_details(
                update_checks=update_checks,
                has_updates=True,
            ),
            confirm_button_text=UPDATE_TOOLS_CONFIRMATION_BUTTON,
            canceled_status_message=UPDATE_TOOLS_CANCELED_STATUS_MESSAGE,
            started_status_message=UPDATE_TOOLS_STARTED_STATUS_MESSAGE,
        )

    return ToolUpdateConfirmationText(
        title=REINSTALL_TOOLS_CONFIRMATION_TITLE,
        text=REINSTALL_TOOLS_CONFIRMATION_TEXT,
        informative_text=build_tool_update_confirmation_details(
            update_checks=update_checks,
            has_updates=False,
        ),
        confirm_button_text=REINSTALL_TOOLS_CONFIRMATION_BUTTON,
        canceled_status_message=REINSTALL_TOOLS_CANCELED_STATUS_MESSAGE,
        started_status_message=REINSTALL_TOOLS_STARTED_STATUS_MESSAGE,
    )


def has_available_tool_updates(*, update_checks: tuple[ToolUpdateCheckResult, ...]) -> bool:
    return any(update_check.should_update for update_check in update_checks)


def build_tool_update_confirmation_details(
    *,
    update_checks: tuple[ToolUpdateCheckResult, ...],
    has_updates: bool,
) -> str:
    check_lines = tuple(
        format_tool_update_check_for_confirmation(update_check=update_check)
        for update_check in update_checks
    )

    header = "Найдены обновления:" if has_updates else "Результат проверки:"
    formatted_checks = "\n".join(f"- {line}" for line in check_lines)

    return (
        f"{header}\n"
        f"{formatted_checks}\n\n"
        "После подтверждения YaLoader скачает свежие сборки FFmpeg и Deno, "
        "подготовит их во временной папке и заменит текущие файлы инструментов."
    )


def format_tool_update_check_for_confirmation(*, update_check: ToolUpdateCheckResult) -> str:
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
