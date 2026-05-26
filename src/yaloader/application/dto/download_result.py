from __future__ import annotations

from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from yaloader.domain.enums import DownloadStatus


class DownloadResult(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    task_id: UUID
    status: DownloadStatus
    output_path: Path | None = None
    error_message: str | None = None

    @classmethod
    def completed(cls, *, task_id: UUID, output_path: Path | None = None) -> DownloadResult:
        return cls(
            task_id=task_id,
            status=DownloadStatus.COMPLETED,
            output_path=output_path,
        )

    @classmethod
    def failed(cls, *, task_id: UUID, error_message: str) -> DownloadResult:
        return cls(
            task_id=task_id,
            status=DownloadStatus.FAILED,
            error_message=error_message,
        )

    @classmethod
    def canceled(cls, *, task_id: UUID) -> DownloadResult:
        return cls(
            task_id=task_id,
            status=DownloadStatus.CANCELED,
            error_message="Загрузка отменена пользователем.",
        )
