from __future__ import annotations

from typing import Final

DEFAULT_STATUS_MESSAGE: Final = "Готов к работе"
TRANSIENT_STATUS_MESSAGE_DURATION_MS: Final = 3000

TRANSIENT_STATUS_MESSAGE_BLINK_DURATION_MS: Final = 1500
TRANSIENT_STATUS_MESSAGE_MIN_OPACITY: Final = 0.45

PRIMARY_DOWNLOAD_STATUS_PREFIXES: Final[tuple[str, ...]] = (
    "Загрузка запущена:",
    "Отмена загрузки...",
    "Ошибка загрузки:",
    "Загрузка завершилась ошибкой:",
)


def is_primary_download_status_message(*, message: str) -> bool:
    return message.startswith(PRIMARY_DOWNLOAD_STATUS_PREFIXES)
