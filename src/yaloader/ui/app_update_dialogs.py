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
            "Приложение скачает новый YaLoader.exe из GitHub Releases и проверит "
            "SHA-256 перед заменой.\n\n"
            "После подготовки обновления YaLoader будет закрыт и запущен заново.\n\n"
            "Не будут затронуты:\n"
            "• история загрузок;\n"
            "• settings.json;\n"
            "• cookies.txt;\n"
            "• FFmpeg и Deno;\n"
            "• пользовательский runtime yt-dlp;\n"
            "• папка загрузок.\n\n"
            "Если замена exe не получится, updater попробует вернуть предыдущий файл."
        ),
        confirm_button_text="Обновить YaLoader",
    )
