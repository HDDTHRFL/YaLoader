from __future__ import annotations

from typing import cast, override

from PyQt6.QtCore import QEvent, QObject, QSignalBlocker, Qt, QTimer
from PyQt6.QtWidgets import QAbstractScrollArea, QScrollBar, QWidget

OVERLAY_SCROLL_BAR_WIDTH = 8
OVERLAY_SCROLL_BAR_RIGHT_MARGIN = -1
OVERLAY_SCROLL_BAR_VERTICAL_MARGIN = 6
OVERLAY_SCROLL_SINGLE_STEP = 12


class OverlayVerticalScrollBarController(QObject):
    def __init__(self, *, scroll_area: QAbstractScrollArea) -> None:
        super().__init__(scroll_area)

        self._scroll_area = scroll_area
        self._native_scroll_bar = cast(QScrollBar, scroll_area.verticalScrollBar())
        self._viewport = cast(QWidget, scroll_area.viewport())
        self._overlay_scroll_bar = QScrollBar(
            Qt.Orientation.Vertical,
            self._viewport,
        )

        self._configure_scroll_bars()
        self._connect_signals()
        self._install_event_filters()
        self.sync()

    def sync(self) -> None:
        self._sync_range()
        self._sync_value_from_native()
        self._sync_geometry()
        self._sync_visibility()

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

        if event.type() in {
            QEvent.Type.Enter,
            QEvent.Type.MouseMove,
            QEvent.Type.Wheel,
        }:
            self._sync_visibility()

        if event.type() == QEvent.Type.Leave:
            self._schedule_visibility_sync()

        return super().eventFilter(watched, event)

    def _configure_scroll_bars(self) -> None:
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setMouseTracking(True)
        self._viewport.setMouseTracking(True)

        self._native_scroll_bar.setSingleStep(OVERLAY_SCROLL_SINGLE_STEP)
        self._overlay_scroll_bar.setObjectName("OverlayScrollBar")
        self._overlay_scroll_bar.setSingleStep(OVERLAY_SCROLL_SINGLE_STEP)
        self._overlay_scroll_bar.setMouseTracking(True)
        self._overlay_scroll_bar.hide()

    def _connect_signals(self) -> None:
        self._native_scroll_bar.rangeChanged.connect(self._handle_native_range_changed)
        self._native_scroll_bar.valueChanged.connect(self._handle_native_value_changed)
        self._overlay_scroll_bar.valueChanged.connect(self._handle_overlay_value_changed)

    def _install_event_filters(self) -> None:
        self._viewport.installEventFilter(self)
        self._scroll_area.installEventFilter(self)
        self._overlay_scroll_bar.installEventFilter(self)

    def _handle_native_range_changed(self, _minimum: int, _maximum: int) -> None:
        self._sync_range()
        self._sync_geometry()
        self._sync_visibility()

    def _handle_native_value_changed(self, _value: int) -> None:
        self._sync_value_from_native()
        self._sync_visibility()

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

    def _sync_value_from_native(self) -> None:
        if self._overlay_scroll_bar.value() == self._native_scroll_bar.value():
            return

        blocker = QSignalBlocker(self._overlay_scroll_bar)
        self._overlay_scroll_bar.setValue(self._native_scroll_bar.value())
        del blocker

    def _sync_geometry(self) -> None:
        viewport_rect = self._viewport.rect()
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

    def _schedule_visibility_sync(self) -> None:
        QTimer.singleShot(0, self._sync_visibility)

    def _sync_visibility(self) -> None:
        should_show = self._has_scrollable_range() and self._is_pointer_inside_scroll_area()
        self._overlay_scroll_bar.setVisible(should_show)

        if should_show:
            self._overlay_scroll_bar.raise_()

    def _has_scrollable_range(self) -> bool:
        return self._native_scroll_bar.maximum() > self._native_scroll_bar.minimum()

    def _is_pointer_inside_scroll_area(self) -> bool:
        return (
            self._scroll_area.underMouse()
            or self._viewport.underMouse()
            or self._overlay_scroll_bar.underMouse()
        )
