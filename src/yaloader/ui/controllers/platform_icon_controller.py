from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, SimpleQueue
from uuid import UUID

from loguru import logger

from yaloader.application.ports.platform_icon_resolver import PlatformIconResolver

PLATFORM_ICON_WORKERS_COUNT = 2


@dataclass(frozen=True, slots=True)
class PlatformIconResolutionResult:
    task_id: UUID
    icon_path: Path | None = None


class PlatformIconController:
    def __init__(self, *, resolver: PlatformIconResolver) -> None:
        self._resolver = resolver
        self._events: SimpleQueue[PlatformIconResolutionResult] = SimpleQueue()
        self._executor = ThreadPoolExecutor(
            max_workers=PLATFORM_ICON_WORKERS_COUNT,
            thread_name_prefix="yaloader-platform-icon",
        )

    def start_resolution(self, *, task_id: UUID, url: str) -> bool:
        self._executor.submit(
            self._resolve_worker,
            task_id=task_id,
            url=url,
        )
        return True

    def drain_results(self) -> tuple[PlatformIconResolutionResult, ...]:
        results: list[PlatformIconResolutionResult] = []

        while True:
            try:
                results.append(self._events.get_nowait())
            except Empty:
                return tuple(results)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _resolve_worker(self, *, task_id: UUID, url: str) -> None:
        try:
            icon_path = self._resolver.resolve_icon_path(url=url)
        except Exception as error:
            logger.debug(
                "Failed to resolve platform favicon. task_id={} url={} error={}",
                task_id,
                url,
                error,
            )
            icon_path = None

        self._events.put(
            PlatformIconResolutionResult(
                task_id=task_id,
                icon_path=icon_path,
            )
        )
