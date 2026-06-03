from __future__ import annotations

from typing import cast, override

from PyQt6.QtCore import QEvent, QObject, QSignalBlocker, Qt
from PyQt6.QtWidgets import QAbstractScrollArea, QScrollBar, QWidget

OVERLAY_SCROLL_BAR_WIDTH = 8
OVERLAY_SCROLL_BAR_RIGHT_MARGIN = 3
OVERLAY_SCROLL_BAR_VERTICAL_MARGIN = 6
OVERLAY_SCROLL_SINGLE_STEP = 12


class OverlayVerticalScrollBarController(QObject):
    def __init__(self, *, scroll_area: QAbstractScrollArea) -> None:
        super().__init__(scroll_area)

        self._scroll_area = scroll_area
        self._native_scroll_bar = cast(QScrollBar, scroll_area.verticalScrollBar())
        self._overlay_scroll_bar = QScrollBar(
            Qt.Orientation.Vertical,
            cast(QWidget, scroll_area.viewport()),
        )

        self._configure_scroll_bars()
        self._connect_signals()
        self._install_event_filters()
        self.sync()

    def sync(self) -> None:
        self._sync_range()
        self._sync_value_from_native()
        self._sync_geometry()

    @override
    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if event is None:
            return super().eventFilter(watched, event)

        if event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.Hide,
            QEvent.Type.LayoutRequest,
        }:
            self.sync()

        return super().eventFilter(watched, event)

    def _configure_scroll_bars(self) -> None:
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._native_scroll_bar.setSingleStep(OVERLAY_SCROLL_SINGLE_STEP)
        self._overlay_scroll_bar.setObjectName("OverlayScrollBar")
        self._overlay_scroll_bar.setSingleStep(OVERLAY_SCROLL_SINGLE_STEP)
        self._overlay_scroll_bar.hide()

    def _connect_signals(self) -> None:
        self._native_scroll_bar.rangeChanged.connect(self._handle_native_range_changed)
        self._native_scroll_bar.valueChanged.connect(self._handle_native_value_changed)
        self._overlay_scroll_bar.valueChanged.connect(self._handle_overlay_value_changed)

    def _install_event_filters(self) -> None:
        viewport = cast(QWidget, self._scroll_area.viewport())
        viewport.installEventFilter(self)
        self._scroll_area.installEventFilter(self)

    def _handle_native_range_changed(self, _minimum: int, _maximum: int) -> None:
        self._sync_range()
        self._sync_geometry()

    def _handle_native_value_changed(self, _value: int) -> None:
        self._sync_value_from_native()

    def _handle_overlay_value_changed(self, value: int) -> None:
        if self._native_scroll_bar.value() == value:
            return

        self._native_scroll_bar.setValue(value)

    def _sync_range(self) -> None:
        blocker = QSignalBlocker(self._overlay_scroll_bar)
        self._overlay_scroll_bar.setRange(
            self._native_scroll_bar.minimum(),
            self._native_scroll_bar.maximum(),
        )
        self._overlay_scroll_bar.setPageStep(self._native_scroll_bar.pageStep())
        self._overlay_scroll_bar.setSingleStep(self._native_scroll_bar.singleStep())
        del blocker

        self._overlay_scroll_bar.setVisible(
            self._native_scroll_bar.maximum() > self._native_scroll_bar.minimum()
        )

        if self._overlay_scroll_bar.isVisible():
            self._overlay_scroll_bar.raise_()

    def _sync_value_from_native(self) -> None:
        if self._overlay_scroll_bar.value() == self._native_scroll_bar.value():
            return

        blocker = QSignalBlocker(self._overlay_scroll_bar)
        self._overlay_scroll_bar.setValue(self._native_scroll_bar.value())
        del blocker

    def _sync_geometry(self) -> None:
        viewport = cast(QWidget, self._scroll_area.viewport())
        viewport_rect = viewport.rect()
        height = max(0, viewport_rect.height() - OVERLAY_SCROLL_BAR_VERTICAL_MARGIN * 2)
        x_position = (
            viewport_rect.right() - OVERLAY_SCROLL_BAR_WIDTH - OVERLAY_SCROLL_BAR_RIGHT_MARGIN + 1
        )

        self._overlay_scroll_bar.setGeometry(
            x_position,
            OVERLAY_SCROLL_BAR_VERTICAL_MARGIN,
            OVERLAY_SCROLL_BAR_WIDTH,
            height,
        )

        if self._overlay_scroll_bar.isVisible():
            self._overlay_scroll_bar.raise_()
