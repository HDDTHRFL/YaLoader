from __future__ import annotations

from datetime import datetime
from typing import Final

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.domain.enums import DownloadStatus, VideoQuality

STATUS_TEXT: Final[dict[DownloadStatus, str]] = {
    DownloadStatus.COMPLETED: "Готово",
    DownloadStatus.FAILED: "Ошибка",
    DownloadStatus.CANCELED: "Отменено",
    DownloadStatus.PENDING: "Ожидает",
    DownloadStatus.RUNNING: "Выполняется",
}


def format_history_title(*, record: DownloadHistoryRecord) -> str | None:
    if record.title is None:
        return None

    title = record.title.strip()

    if not title:
        return None

    return title


def format_history_quality(*, record: DownloadHistoryRecord) -> str:
    if record.resolved_video_quality is None:
        return record.video_quality.value

    if record.video_quality is VideoQuality.BEST:
        return f"{record.video_quality.value} ({record.resolved_video_quality.value})"

    if record.video_quality is not record.resolved_video_quality:
        return f"{record.video_quality.value} ({record.resolved_video_quality.value})"

    return record.video_quality.value


def format_history_datetime(value: datetime) -> str:
    return value.astimezone().strftime("%d.%m.%Y %H:%M")
