from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

from yaloader.application.dto.app_update import (
    AppReleaseInfo,
    AppUpdateCheckResult,
    AppUpdateInstallResult,
)

APP_UPDATE_WORKERS_COUNT = 1


class AppUpdateUseCase(Protocol):
    def check_update(self) -> AppUpdateCheckResult: ...

    def install_update(self, *, release_info: AppReleaseInfo) -> AppUpdateInstallResult: ...


@dataclass(frozen=True, slots=True)
class AppUpdateControllerUpdate:
    status_message: str | None = None
    result: AppUpdateCheckResult | None = None
    install_result: AppUpdateInstallResult | None = None


class AppUpdateController:
    def __init__(self, *, service: AppUpdateUseCase) -> None:
        self._service = service
        self._executor = ThreadPoolExecutor(
            max_workers=APP_UPDATE_WORKERS_COUNT,
            thread_name_prefix="yaloader-app-update",
        )
        self._active_check_future: Future[AppUpdateCheckResult] | None = None
        self._active_install_future: Future[AppUpdateInstallResult] | None = None

    @property
    def is_active(self) -> bool:
        return self._active_check_future is not None or self._active_install_future is not None

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def check_update(self) -> AppUpdateControllerUpdate:
        if self.is_active:
            return AppUpdateControllerUpdate(
                status_message="Проверка или обновление YaLoader уже выполняется",
            )

        self._active_check_future = self._executor.submit(self._service.check_update)

        return AppUpdateControllerUpdate(
            status_message="Проверяем обновление YaLoader...",
        )

    def install_update(self, *, release_info: AppReleaseInfo) -> AppUpdateControllerUpdate:
        if self.is_active:
            return AppUpdateControllerUpdate(
                status_message="Проверка или обновление YaLoader уже выполняется",
            )

        self._active_install_future = self._executor.submit(
            self._service.install_update,
            release_info=release_info,
        )

        return AppUpdateControllerUpdate(
            status_message=f"Скачиваем обновление YaLoader {release_info.version}...",
        )

    def poll(self) -> AppUpdateControllerUpdate:
        install_update = self._poll_install_update()

        if install_update.install_result is not None or install_update.status_message is not None:
            return install_update

        return self._poll_check_update()

    def _poll_check_update(self) -> AppUpdateControllerUpdate:
        if self._active_check_future is None:
            return AppUpdateControllerUpdate()

        if not self._active_check_future.done():
            return AppUpdateControllerUpdate()

        try:
            result = self._active_check_future.result()
        except Exception as error:
            self._active_check_future = None
            return AppUpdateControllerUpdate(
                status_message=f"Не удалось проверить обновление YaLoader: {error}",
            )

        self._active_check_future = None
        return AppUpdateControllerUpdate(result=result)

    def _poll_install_update(self) -> AppUpdateControllerUpdate:
        if self._active_install_future is None:
            return AppUpdateControllerUpdate()

        if not self._active_install_future.done():
            return AppUpdateControllerUpdate()

        try:
            install_result = self._active_install_future.result()
        except Exception as error:
            self._active_install_future = None
            return AppUpdateControllerUpdate(
                status_message=f"Не удалось подготовить обновление YaLoader: {error}",
            )

        self._active_install_future = None
        return AppUpdateControllerUpdate(install_result=install_result)
