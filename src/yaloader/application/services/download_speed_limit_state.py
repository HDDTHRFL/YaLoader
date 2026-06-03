from __future__ import annotations

from threading import RLock

from yaloader.domain.download_speed_limit import validate_download_speed_limit_bytes_per_second


class DownloadSpeedLimitState:
    def __init__(self, *, bytes_per_second: int | None = None) -> None:
        self._lock = RLock()
        self._bytes_per_second = validate_download_speed_limit_bytes_per_second(
            bytes_per_second=bytes_per_second,
        )

    def get_download_speed_limit_bytes_per_second(self) -> int | None:
        with self._lock:
            return self._bytes_per_second

    def set_download_speed_limit_bytes_per_second(
        self,
        *,
        bytes_per_second: int | None,
    ) -> None:
        validated_value = validate_download_speed_limit_bytes_per_second(
            bytes_per_second=bytes_per_second,
        )

        with self._lock:
            self._bytes_per_second = validated_value
