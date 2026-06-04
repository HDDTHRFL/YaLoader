from __future__ import annotations

from datetime import datetime
from typing import Final

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.domain.enums import DownloadStatus, VideoQuality
from yaloader.domain.source_media_kind import SourceMediaKind, detect_source_media_kind

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

    source_kind = detect_source_media_kind(
        url=record.url,
        include_playlist=record.include_playlist,
    )

    if source_kind is SourceMediaKind.PLAYLIST:
        if record.playlist_count is not None:
            return f"[PLAYLIST] · {record.playlist_count} · {title}"

        return f"[PLAYLIST] · {title}"

    if source_kind is SourceMediaKind.SHORTS:
        return f"[SHORTS] · {title}"

    return title


def format_history_quality(*, record: DownloadHistoryRecord) -> str:
    quality_text = _format_base_history_quality(record=record)
    source_kind = detect_source_media_kind(
        url=record.url,
        include_playlist=record.include_playlist,
    )

    if source_kind is SourceMediaKind.PLAYLIST:
        return f"{quality_text} · playlist"

    if source_kind is SourceMediaKind.SHORTS:
        return f"{quality_text} · shorts"

    return quality_text


def format_history_datetime(value: datetime) -> str:
    return value.astimezone().strftime("%d.%m.%Y %H:%M")


def _format_base_history_quality(*, record: DownloadHistoryRecord) -> str:
    if record.resolved_video_quality is None:
        return record.video_quality.value

    if record.video_quality is VideoQuality.BEST:
        return f"{record.video_quality.value} ({record.resolved_video_quality.value})"

    if record.video_quality is not record.resolved_video_quality:
        return f"{record.video_quality.value} ({record.resolved_video_quality.value})"

    return record.video_quality.value
