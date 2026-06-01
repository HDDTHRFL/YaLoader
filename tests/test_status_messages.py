from __future__ import annotations

from yaloader.ui.status_messages import is_primary_download_status_message


def test_download_started_status_is_primary() -> None:
    assert is_primary_download_status_message(
        message="Загрузка запущена: https://www.youtube.com/watch?v=test"
    )


def test_download_canceling_status_is_primary() -> None:
    assert is_primary_download_status_message(
        message="Отмена загрузки... Частичные файлы будут удалены"
    )


def test_download_error_status_is_primary() -> None:
    assert is_primary_download_status_message(message="Загрузка завершилась ошибкой: network error")


def test_queue_completed_status_is_not_primary() -> None:
    assert not is_primary_download_status_message(message="Очередь загрузок завершена")


def test_environment_refresh_status_is_not_primary() -> None:
    assert not is_primary_download_status_message(message="Состояние системы обновлено")
