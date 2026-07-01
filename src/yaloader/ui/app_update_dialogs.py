from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from yaloader.ui.widgets.common.confirmation_dialogs import confirm_informational_action


def confirm_app_update_installation(
    *,
    parent: QWidget,
    latest_version: str,
) -> bool:
    return confirm_informational_action(
        parent=parent,
        title="Обновить YaLoader?",
        text=f"YaLoader будет обновлён до версии {latest_version}.",
        informative_text=(
            "После подготовки обновления YaLoader будет закрыт и запущен заново.\n\n"
            "Не будут затронуты:\n"
            "• история загрузок;\n"
            "• настройки приложения;\n"
            "• cookies\n"
            "• FFmpeg и Deno;\n"
            "• пользовательский yt-dlp;\n"
            "• папка загрузок."
        ),
        confirm_button_text="Обновить YaLoader",
    )
