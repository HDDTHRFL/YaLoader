from __future__ import annotations

from enum import StrEnum

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QPushButton, QWidget

from yaloader.application.dto.tool_installation import ToolUpdateCheckResult
from yaloader.ui.widgets.common.confirmation_dialogs import (
    CONFIRMATION_DIALOG_STYLE_SHEET,
    confirm_dangerous_action,
    confirm_informational_action,
)


class YtDlpFailureRecoveryAction(StrEnum):
    TRY_BUNDLED = "try_bundled"
    RESET = "reset"
    NONE = "none"


def confirm_ytdlp_update(
    *,
    parent: QWidget,
    update_check: ToolUpdateCheckResult,
) -> bool:
    latest_version = update_check.latest_version or "новая версия"
    current_version = update_check.current_version or "текущая версия"

    return confirm_informational_action(
        parent=parent,
        title="Обновить yt-dlp?",
        text=f"Доступна версия yt-dlp {latest_version}.",
        informative_text=(
            f"Сейчас используется {current_version}.\n\n"
            "YaLoader скачает wheel yt-dlp с PyPI, распакует его в отдельную "
            "пользовательскую runtime-папку и проверит перед подключением.\n\n"
            "Встроенный yt-dlp останется внутри приложения. Если пользовательская версия "
            "окажется повреждена, YaLoader автоматически вернётся к встроенной версии."
        ),
        confirm_button_text="Обновить yt-dlp",
    )


def confirm_reset_ytdlp_runtime(*, parent: QWidget) -> bool:
    return confirm_dangerous_action(
        parent=parent,
        title="Сбросить yt-dlp?",
        text="Пользовательский yt-dlp будет удалён.",
        informative_text=(
            "После сброса YaLoader снова будет использовать встроенную версию yt-dlp, "
            "которая поставляется вместе с приложением.\n\n"
            "Скачанные видео, cookies.txt, история и настройки не удаляются."
        ),
        confirm_button_text="Сбросить yt-dlp",
    )


def choose_ytdlp_failure_recovery_action(
    *,
    parent: QWidget,
    external_version: str,
    bundled_version: str,
) -> YtDlpFailureRecoveryAction:
    message_box = QMessageBox(parent)
    message_box.setWindowTitle("Ошибка пользовательского yt-dlp")
    message_box.setIcon(QMessageBox.Icon.Warning)
    message_box.setText(f"Загрузка не удалась на пользовательском yt-dlp {external_version}.")
    message_box.setInformativeText(
        "Можно попробовать повторить загрузку на встроенной версии "
        f"yt-dlp {bundled_version} или просто сбросить пользовательский yt-dlp."
    )
    message_box.setTextFormat(Qt.TextFormat.PlainText)
    message_box.setModal(True)
    message_box.setStyleSheet(CONFIRMATION_DIALOG_STYLE_SHEET)

    try_bundled_button = QPushButton(
        f"Попробовать встроенный yt-dlp {bundled_version}",
        message_box,
    )
    try_bundled_button.setObjectName("DialogSuccessButton")
    try_bundled_button.setCursor(Qt.CursorShape.PointingHandCursor)

    reset_button = QPushButton("Сбросить пользовательский yt-dlp", message_box)
    reset_button.setObjectName("DialogDangerButton")
    reset_button.setCursor(Qt.CursorShape.PointingHandCursor)

    cancel_button = QPushButton("Отмена", message_box)
    cancel_button.setObjectName("DialogSecondaryButton")
    cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)

    message_box.addButton(try_bundled_button, QMessageBox.ButtonRole.AcceptRole)
    message_box.addButton(reset_button, QMessageBox.ButtonRole.DestructiveRole)
    message_box.addButton(cancel_button, QMessageBox.ButtonRole.RejectRole)
    message_box.setDefaultButton(cancel_button)
    message_box.setEscapeButton(cancel_button)

    message_box.exec()
    clicked_button = message_box.clickedButton()

    if clicked_button == try_bundled_button:
        return YtDlpFailureRecoveryAction.TRY_BUNDLED

    if clicked_button == reset_button:
        return YtDlpFailureRecoveryAction.RESET

    return YtDlpFailureRecoveryAction.NONE
