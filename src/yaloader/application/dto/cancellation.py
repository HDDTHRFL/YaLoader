from __future__ import annotations

from threading import Event


class DownloadCancellationToken:
    def __init__(self) -> None:
        self._event = Event()

    def request_cancel(self) -> None:
        self._event.set()

    @property
    def is_cancel_requested(self) -> bool:
        return self._event.is_set()
