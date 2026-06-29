from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

from yaloader.application.dto.app_update import AppUpdateCheckResult

APP_UPDATE_WORKERS_COUNT = 1


class AppUpdateUseCase(Protocol):
    def check_update(self) -> AppUpdateCheckResult: ...


@dataclass(frozen=True, slots=True)
class AppUpdateControllerUpdate:
    status_message: str | None = None
    result: AppUpdateCheckResult | None = None


class AppUpdateController:
    def __init__(self, *, service: AppUpdateUseCase) -> None:
        self._service = service
        self._executor = ThreadPoolExecutor(
            max_workers=APP_UPDATE_WORKERS_COUNT,
            thread_name_prefix="yaloader-app-update",
        )
        self._active_future: Future[AppUpdateCheckResult] | None = None

    @property
    def is_active(self) -> bool:
        return self._active_future is not None

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def check_update(self) -> AppUpdateControllerUpdate:
        if self.is_active:
            return AppUpdateControllerUpdate(
                status_message="Проверка обновления YaLoader уже выполняется",
            )

        self._active_future = self._executor.submit(self._service.check_update)

        return AppUpdateControllerUpdate(
            status_message="Проверяем обновление YaLoader...",
        )

    def poll(self) -> AppUpdateControllerUpdate:
        if self._active_future is None:
            return AppUpdateControllerUpdate()

        if not self._active_future.done():
            return AppUpdateControllerUpdate()

        try:
            result = self._active_future.result()
        except Exception as error:
            self._active_future = None
            return AppUpdateControllerUpdate(
                status_message=f"Не удалось проверить обновление YaLoader: {error}",
            )

        self._active_future = None
        return AppUpdateControllerUpdate(result=result)
