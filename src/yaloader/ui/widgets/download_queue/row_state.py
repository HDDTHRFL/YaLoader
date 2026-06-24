from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from yaloader.domain.entities.download_task import DownloadTask


@dataclass(frozen=True, slots=True)
class QueueTableRowState:
    task: DownloadTask
    is_metadata_resolution_pending: bool = False
    is_metadata_resolution_failed: bool = False
    is_download_preparation_running: bool = False
    is_download_prepared: bool = False
    platform_icon_path: Path | None = None
    copy_feedback_generation: int | None = None

    @classmethod
    def create(cls, *, task: DownloadTask) -> QueueTableRowState:
        return cls(task=task)

    @property
    def is_quality_resolution_pending(self) -> bool:
        return self.is_metadata_resolution_pending

    def with_task(self, *, task: DownloadTask) -> QueueTableRowState:
        return replace(self, task=task)

    def with_metadata_resolution_pending(
        self,
        *,
        is_pending: bool,
    ) -> QueueTableRowState:
        return replace(self, is_metadata_resolution_pending=is_pending)

    def with_quality_resolution_pending(
        self,
        *,
        is_pending: bool,
    ) -> QueueTableRowState:
        return self.with_metadata_resolution_pending(is_pending=is_pending)

    def with_metadata_resolution_failed(
        self,
        *,
        is_failed: bool,
    ) -> QueueTableRowState:
        return replace(self, is_metadata_resolution_failed=is_failed)

    def with_download_preparation_running(
        self,
        *,
        is_running: bool,
    ) -> QueueTableRowState:
        return replace(self, is_download_preparation_running=is_running)

    def with_download_prepared(
        self,
        *,
        is_prepared: bool,
    ) -> QueueTableRowState:
        return replace(self, is_download_prepared=is_prepared)

    def with_platform_icon_path(
        self,
        *,
        icon_path: Path | None,
    ) -> QueueTableRowState:
        return replace(self, platform_icon_path=icon_path)

    def with_copy_feedback_generation(
        self,
        *,
        generation: int | None,
    ) -> QueueTableRowState:
        return replace(self, copy_feedback_generation=generation)
