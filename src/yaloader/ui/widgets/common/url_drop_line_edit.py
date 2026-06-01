from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, cast, override

from PyQt6.QtCore import QMimeData
from PyQt6.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QResizeEvent,
)
from PyQt6.QtWidgets import QLineEdit, QWidget

from yaloader.domain.source_policy import validate_supported_media_url
from yaloader.domain.value_objects.media_url import MediaUrl
from yaloader.ui.widgets.common.drop_highlight import DropHighlightOverlay
from yaloader.ui.widgets.common.url_extraction import (
    HTTP_URL_PATTERN,
    extract_first_http_url_from_candidates,
    normalize_url_candidate,
)

DropUrlEvent = QDragEnterEvent | QDragMoveEvent | QDropEvent


class MimeDataProvider(Protocol):
    def mimeData(self) -> QMimeData: ...  # noqa: N802


class UrlDropLineEdit(QLineEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._drop_highlight_overlay = DropHighlightOverlay(parent=self)

        self.setAcceptDrops(True)
        self._sync_drop_highlight_geometry()

    def set_drop_highlight_active(self, *, is_active: bool) -> None:
        self._sync_drop_highlight_geometry()
        self._drop_highlight_overlay.set_active(is_active=is_active)

    @override
    def dragEnterEvent(self, event: QDragEnterEvent | None) -> None:
        if self._accept_supported_url_drag_event(event=event):
            return

        super().dragEnterEvent(event)

    @override
    def dragMoveEvent(self, event: QDragMoveEvent | None) -> None:
        if self._accept_supported_url_drag_event(event=event):
            return

        super().dragMoveEvent(event)

    @override
    def dragLeaveEvent(self, event: QDragLeaveEvent | None) -> None:
        self.set_drop_highlight_active(is_active=False)
        super().dragLeaveEvent(event)

    @override
    def dropEvent(self, event: QDropEvent | None) -> None:
        self.set_drop_highlight_active(is_active=False)

        if event is None:
            return

        dropped_url = extract_first_supported_media_url_from_drop_event(event=event)

        if dropped_url is None:
            super().dropEvent(event)
            return

        self.setText(dropped_url)
        self.setFocus()
        self.setCursorPosition(len(dropped_url))

        event.acceptProposedAction()

    @override
    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._sync_drop_highlight_geometry()

    def _accept_supported_url_drag_event(
        self,
        *,
        event: QDragEnterEvent | QDragMoveEvent | None,
    ) -> bool:
        if event is None:
            self.set_drop_highlight_active(is_active=False)
            return False

        if extract_first_supported_media_url_from_drop_event(event=event) is None:
            self.set_drop_highlight_active(is_active=False)
            return False

        self.set_drop_highlight_active(is_active=True)
        event.acceptProposedAction()
        return True

    def _sync_drop_highlight_geometry(self) -> None:
        self._drop_highlight_overlay.sync_geometry()


def extract_first_http_url_from_drop_event(*, event: DropUrlEvent) -> str | None:
    mime_data_provider = cast(MimeDataProvider, event)
    return extract_first_http_url_from_mime_data(mime_data=mime_data_provider.mimeData())


def extract_first_http_url_from_mime_data(*, mime_data: QMimeData) -> str | None:
    url_candidates = tuple(url.toString() for url in mime_data.urls())

    dropped_url = extract_first_http_url_from_candidates(candidates=url_candidates)

    if dropped_url is not None:
        return dropped_url

    if not mime_data.hasText():
        return None

    return extract_first_http_url_from_candidates(candidates=(mime_data.text(),))


def extract_first_supported_media_url_from_drop_event(*, event: DropUrlEvent) -> str | None:
    mime_data_provider = cast(MimeDataProvider, event)
    return extract_first_supported_media_url_from_mime_data(mime_data=mime_data_provider.mimeData())


def extract_first_supported_media_url_from_mime_data(*, mime_data: QMimeData) -> str | None:
    url_candidates = tuple(url.toString() for url in mime_data.urls())

    dropped_url = extract_first_supported_media_url_from_candidates(candidates=url_candidates)

    if dropped_url is not None:
        return dropped_url

    if not mime_data.hasText():
        return None

    return extract_first_supported_media_url_from_candidates(candidates=(mime_data.text(),))


def extract_first_supported_media_url_from_candidates(
    *,
    candidates: Iterable[str],
) -> str | None:
    for candidate in candidates:
        direct_url = normalize_supported_media_url_candidate(candidate=candidate)

        if direct_url is not None:
            return direct_url

        for match in HTTP_URL_PATTERN.finditer(candidate):
            matched_url = normalize_supported_media_url_candidate(candidate=match.group(0))

            if matched_url is not None:
                return matched_url

    return None


def normalize_supported_media_url_candidate(*, candidate: str) -> str | None:
    normalized_candidate = normalize_url_candidate(candidate=candidate)

    try:
        media_url = MediaUrl(value=normalized_candidate)
        return validate_supported_media_url(url=media_url.value)
    except ValueError:
        return None
