from __future__ import annotations

from enum import StrEnum


class DownloadMode(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"


class OutputFormat(StrEnum):
    MP4 = "mp4"
    WEBM = "webm"
    MP3 = "mp3"
    M4A = "m4a"


class VideoQuality(StrEnum):
    BEST = "best"
    P2160 = "2160p"
    P1440 = "1440p"
    P1080 = "1080p"
    P720 = "720p"


class DownloadStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
