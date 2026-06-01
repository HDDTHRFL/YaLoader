from __future__ import annotations

from dataclasses import dataclass, replace

from yaloader.domain.entities.download_task import DownloadTask


@dataclass(frozen=True, slots=True)
class QueueTableRowState:
    task: DownloadTask
    is_quality_resolution_pending: bool = False
    is_metadata_resolution_failed: bool = False
    copy_feedback_generation: int | None = None

    @classmethod
    def create(cls, *, task: DownloadTask) -> QueueTableRowState:
        return cls(task=task)

    def with_task(self, *, task: DownloadTask) -> QueueTableRowState:
        return replace(self, task=task)

    def with_quality_resolution_pending(
        self,
        *,
        is_pending: bool,
    ) -> QueueTableRowState:
        return replace(self, is_quality_resolution_pending=is_pending)

    def with_metadata_resolution_failed(
        self,
        *,
        is_failed: bool,
    ) -> QueueTableRowState:
        return replace(self, is_metadata_resolution_failed=is_failed)

    def with_copy_feedback_generation(
        self,
        *,
        generation: int | None,
    ) -> QueueTableRowState:
        return replace(self, copy_feedback_generation=generation)
