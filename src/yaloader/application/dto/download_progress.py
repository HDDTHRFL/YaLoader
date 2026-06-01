from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MIN_PERCENT = 0
MAX_PERCENT = 100


class DownloadProgress(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    task_id: UUID
    percent: float | None = Field(default=None, ge=MIN_PERCENT, le=MAX_PERCENT)
    status_text: str = Field(min_length=1)
    downloaded_bytes: int | None = None
    total_bytes: int | None = None
    speed_bytes_per_second: int | None = None

    @classmethod
    def started(cls, *, task_id: UUID) -> DownloadProgress:
        return cls(
            task_id=task_id,
            percent=0,
            status_text="Ожидание",
        )

    @classmethod
    def processing(cls, *, task_id: UUID) -> DownloadProgress:
        return cls(
            task_id=task_id,
            percent=100,
            status_text="Обработка",
        )

    @classmethod
    def completed(cls, *, task_id: UUID) -> DownloadProgress:
        return cls(
            task_id=task_id,
            percent=100,
            status_text="Готово",
        )

    @classmethod
    def failed(cls, *, task_id: UUID) -> DownloadProgress:
        return cls(
            task_id=task_id,
            percent=None,
            status_text="Ошибка",
        )

    @classmethod
    def canceled(cls, *, task_id: UUID) -> DownloadProgress:
        return cls(
            task_id=task_id,
            percent=None,
            status_text="Отменено",
        )

    @property
    def progress_bar_value(self) -> int:
        if self.percent is None:
            return 0

        return max(MIN_PERCENT, min(MAX_PERCENT, round(self.percent)))
