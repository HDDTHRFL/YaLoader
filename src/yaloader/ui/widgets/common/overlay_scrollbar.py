from __future__ import annotations

from contextlib import suppress
from typing import cast, override

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSignalBlocker,
    Qt,
    QTimer,
)
from PyQt6.QtGui import QColor, QCursor, QPainter, QPaintEvent
from PyQt6.QtWidgets import (
    QAbstractScrollArea,
    QGraphicsOpacityEffect,
    QScrollBar,
    QStyle,
    QWidget,
)

OVERLAY_SCROLL_BAR_IDLE_TRACK_WIDTH = 9
OVERLAY_SCROLL_BAR_HOVER_TRACK_WIDTH = 10
OVERLAY_SCROLL_BAR_IDLE_HANDLE_WIDTH = 5.0
OVERLAY_SCROLL_BAR_HOVER_HANDLE_WIDTH = 6.0
OVERLAY_SCROLL_BAR_RIGHT_MARGIN = 1
OVERLAY_SCROLL_BAR_VERTICAL_MARGIN = 6
OVERLAY_SCROLL_SINGLE_STEP = 12
OVERLAY_SCROLL_BAR_MIN_HANDLE_HEIGHT = 32
OVERLAY_SCROLL_BAR_HANDLE_RIGHT_PADDING = 1.5

OVERLAY_SCROLLBAR_SHOW_DURATION_MS = 95
OVERLAY_SCROLLBAR_HIDE_DURATION_MS = 170
OVERLAY_SCROLLBAR_VISIBILITY_CHECK_INTERVAL_MS = 180

OVERLAY_SCROLL_BAR_IDLE_COLOR = QColor(139, 148, 158, 132)
OVERLAY_SCROLL_BAR_HOVER_COLOR = QColor(201, 209, 217, 185)
OVERLAY_SCROLL_BAR_PRESSED_COLOR = QColor(240, 246, 252, 220)


class RoundedOverlayScrollBar(QScrollBar):
    @override
    def paintEvent(self, event: QPaintEvent | None) -> None:
        if not self.isVisible():
            return

        handle_rect = self._calculate_handle_rect()

        if handle_rect.isNull() or handle_rect.isEmpty():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._handle_color())
        radius = min(handle_rect.width(), handle_rect.height()) / 2.0
        painter.drawRoundedRect(handle_rect, radius, radius)
        painter.end()

        if event is not None:
            event.accept()

    def _calculate_handle_rect(self) -> QRectF:
        minimum = self.minimum()
        maximum = self.maximum()

        if maximum <= minimum:
            return QRectF()

        track_height = max(0, self.height())

        if track_height <= 0:
            return QRectF()

        page_step = max(1, self.pageStep())
        range_size = maximum - minimum
        document_size = range_size + page_step
        handle_height = max(
            OVERLAY_SCROLL_BAR_MIN_HANDLE_HEIGHT,
            round(track_height * page_step / document_size),
        )
        handle_height = min(handle_height, track_height)

        max_top = max(0, track_height - handle_height)
        progress = (self.value() - minimum) / range_size
        top_position = round(max_top * progress)

        handle_width = self._handle_width()
        right_padding = min(
            OVERLAY_SCROLL_BAR_HANDLE_RIGHT_PADDING,
            max(0.0, self.width() - handle_width),
        )
        left_position = max(0.0, self.width() - handle_width - right_padding)

        return QRectF(
            left_position,
            float(top_position),
            handle_width,
            float(handle_height),
        )

    def _handle_color(self) -> QColor:
        if self.isSliderDown():
            return OVERLAY_SCROLL_BAR_PRESSED_COLOR

        if self.property("expanded") is True:
            return OVERLAY_SCROLL_BAR_HOVER_COLOR

        return OVERLAY_SCROLL_BAR_IDLE_COLOR

    def _handle_width(self) -> float:
        if self.property("expanded") is True:
            return OVERLAY_SCROLL_BAR_HOVER_HANDLE_WIDTH

        return OVERLAY_SCROLL_BAR_IDLE_HANDLE_WIDTH


class OverlayVerticalScrollBarController(QObject):
    def __init__(self, *, scroll_area: QAbstractScrollArea) -> None:
        super().__init__(scroll_area)

        self._scroll_area = scroll_area
        self._native_scroll_bar = cast(QScrollBar, scroll_area.verticalScrollBar())
        self._viewport = cast(QWidget, scroll_area.viewport())
        self._overlay_scroll_bar = RoundedOverlayScrollBar(
            Qt.Orientation.Vertical,
            scroll_area,
        )
        self._opacity_effect = QGraphicsOpacityEffect(self._overlay_scroll_bar)
        self._opacity_animation = QPropertyAnimation(
            self._opacity_effect,
            b"opacity",
            self,
        )
        self._visibility_timer = QTimer(self)
        self._is_overlay_visible = False
        self._is_overlay_hovered = False
        self._is_overlay_pressed = False
        self._visibility_generation = 0

        self._configure_scroll_bars()
        self._configure_opacity_animation()
        self._configure_visibility_timer()
        self._connect_signals()
        self._install_event_filters()
        self.sync()

    def sync(self) -> None:
        self._sync_range()
        self._sync_value_from_native()
        self._sync_hover_state()
        self._sync_geometry()
        self._sync_visibility()

    @override
    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if event is None:
            return super().eventFilter(watched, event)

        event_type = event.type()

        if event_type in {
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.Hide,
            QEvent.Type.LayoutRequest,
        }:
            self.sync()

        if event_type in {
            QEvent.Type.Enter,
            QEvent.Type.MouseMove,
            QEvent.Type.Wheel,
        }:
            self._sync_hover_state()
            self._sync_visibility()

        if event_type == QEvent.Type.Leave:
            self._sync_hover_state()
            self._schedule_visibility_sync()

        if watched == self._overlay_scroll_bar:
            self._handle_overlay_scroll_bar_event(event_type=event_type)

        return super().eventFilter(watched, event)

    def _configure_scroll_bars(self) -> None:
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setMouseTracking(True)
        self._viewport.setMouseTracking(True)

        self._native_scroll_bar.setSingleStep(OVERLAY_SCROLL_SINGLE_STEP)
        self._overlay_scroll_bar.setObjectName("OverlayScrollBar")
        self._overlay_scroll_bar.setProperty("expanded", False)
        self._overlay_scroll_bar.setSingleStep(OVERLAY_SCROLL_SINGLE_STEP)
        self._overlay_scroll_bar.setMouseTracking(True)
        self._overlay_scroll_bar.setGraphicsEffect(self._opacity_effect)
        self._overlay_scroll_bar.hide()

    def _configure_opacity_animation(self) -> None:
        self._opacity_effect.setOpacity(0.0)
        self._opacity_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def _configure_visibility_timer(self) -> None:
        self._visibility_timer.setInterval(OVERLAY_SCROLLBAR_VISIBILITY_CHECK_INTERVAL_MS)
        self._visibility_timer.timeout.connect(self._sync_visibility)

    def _connect_signals(self) -> None:
        self._native_scroll_bar.rangeChanged.connect(self._handle_native_range_changed)
        self._native_scroll_bar.valueChanged.connect(self._handle_native_value_changed)
        self._overlay_scroll_bar.valueChanged.connect(self._handle_overlay_value_changed)

    def _install_event_filters(self) -> None:
        self._viewport.installEventFilter(self)
        self._scroll_area.installEventFilter(self)
        self._overlay_scroll_bar.installEventFilter(self)

    def _handle_overlay_scroll_bar_event(self, *, event_type: QEvent.Type) -> None:
        if event_type == QEvent.Type.MouseButtonPress:
            self._is_overlay_pressed = True
            self._sync_hover_state()
            self._sync_visibility()
            self._overlay_scroll_bar.update()
            return

        if event_type == QEvent.Type.MouseButtonRelease:
            self._is_overlay_pressed = False
            self._sync_hover_state()
            self._overlay_scroll_bar.update()
            self._schedule_visibility_sync()

    def _handle_native_range_changed(self, _minimum: int, _maximum: int) -> None:
        self._sync_range()
        self._sync_geometry()
        self._sync_visibility()
        self._overlay_scroll_bar.update()

    def _handle_native_value_changed(self, _value: int) -> None:
        self._sync_value_from_native()
        self._sync_visibility()
        self._overlay_scroll_bar.update()

    def _handle_overlay_value_changed(self, value: int) -> None:
        if self._native_scroll_bar.value() == value:
            return

        self._native_scroll_bar.setValue(value)
        self._overlay_scroll_bar.update()

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

    def _sync_hover_state(self) -> None:
        is_hovered = self._is_overlay_pressed or self._is_pointer_inside_widget(
            widget=self._overlay_scroll_bar,
        )

        if self._is_overlay_hovered == is_hovered:
            return

        self._is_overlay_hovered = is_hovered
        self._overlay_scroll_bar.setProperty("expanded", is_hovered)
        self._refresh_overlay_scroll_bar_style()
        self._sync_geometry()
        self._overlay_scroll_bar.update()

    def _sync_geometry(self) -> None:
        viewport_geometry = self._viewport.geometry()
        scroll_bar_width = self._current_overlay_scroll_bar_width()
        height = max(0, viewport_geometry.height() - OVERLAY_SCROLL_BAR_VERTICAL_MARGIN * 2)
        x_position = (
            viewport_geometry.right() - scroll_bar_width - OVERLAY_SCROLL_BAR_RIGHT_MARGIN + 1
        )

        self._overlay_scroll_bar.setGeometry(
            x_position,
            viewport_geometry.top() + OVERLAY_SCROLL_BAR_VERTICAL_MARGIN,
            scroll_bar_width,
            height,
        )

        if self._overlay_scroll_bar.isVisible():
            self._overlay_scroll_bar.raise_()

    def _schedule_visibility_sync(self) -> None:
        QTimer.singleShot(0, self._sync_visibility)

    def _sync_visibility(self) -> None:
        self._sync_hover_state()

        should_show = self._has_scrollable_range() and (
            self._is_overlay_pressed or self._is_pointer_inside_scroll_area()
        )
        self._set_overlay_visible(is_visible=should_show)

    def _set_overlay_visible(self, *, is_visible: bool) -> None:
        if self._is_overlay_visible == is_visible:
            return

        self._is_overlay_visible = is_visible
        self._visibility_generation += 1
        generation = self._visibility_generation

        self._opacity_animation.stop()
        self._opacity_animation.setStartValue(self._opacity_effect.opacity())

        if is_visible:
            self._overlay_scroll_bar.show()
            self._overlay_scroll_bar.raise_()
            self._overlay_scroll_bar.update()
            self._start_visibility_timer()
            self._opacity_animation.setDuration(OVERLAY_SCROLLBAR_SHOW_DURATION_MS)
            self._opacity_animation.setEndValue(1.0)
            self._opacity_animation.start()
            return

        self._opacity_animation.setDuration(OVERLAY_SCROLLBAR_HIDE_DURATION_MS)
        self._opacity_animation.setEndValue(0.0)
        self._opacity_animation.finished.connect(
            lambda: self._hide_overlay_after_animation(generation=generation)
        )
        self._opacity_animation.start()

    def _hide_overlay_after_animation(self, *, generation: int) -> None:
        with suppress(TypeError):
            self._opacity_animation.finished.disconnect()

        if generation != self._visibility_generation:
            return

        if self._is_overlay_visible:
            return

        self._is_overlay_pressed = False
        self._sync_hover_state()
        self._overlay_scroll_bar.hide()
        self._stop_visibility_timer()

    def _start_visibility_timer(self) -> None:
        if self._visibility_timer.isActive():
            return

        self._visibility_timer.start()

    def _stop_visibility_timer(self) -> None:
        if not self._visibility_timer.isActive():
            return

        self._visibility_timer.stop()

    def _refresh_overlay_scroll_bar_style(self) -> None:
        style = self._overlay_scroll_bar.style()

        if not isinstance(style, QStyle):
            return

        style.unpolish(self._overlay_scroll_bar)
        style.polish(self._overlay_scroll_bar)

    def _current_overlay_scroll_bar_width(self) -> int:
        if self._is_overlay_hovered:
            return OVERLAY_SCROLL_BAR_HOVER_TRACK_WIDTH

        return OVERLAY_SCROLL_BAR_IDLE_TRACK_WIDTH

    def _has_scrollable_range(self) -> bool:
        return self._native_scroll_bar.maximum() > self._native_scroll_bar.minimum()

    def _is_pointer_inside_scroll_area(self) -> bool:
        global_position = QCursor.pos()

        return (
            self._is_global_position_inside_widget(
                widget=self._scroll_area,
                global_position=global_position,
            )
            or self._is_global_position_inside_widget(
                widget=self._viewport,
                global_position=global_position,
            )
            or self._is_global_position_inside_widget(
                widget=self._overlay_scroll_bar,
                global_position=global_position,
            )
        )

    def _is_pointer_inside_widget(self, *, widget: QWidget) -> bool:
        return self._is_global_position_inside_widget(
            widget=widget,
            global_position=QCursor.pos(),
        )

    def _is_global_position_inside_widget(
        self,
        *,
        widget: QWidget,
        global_position: QPoint,
    ) -> bool:
        if not widget.isVisible():
            return False

        local_position = widget.mapFromGlobal(global_position)
        return widget.rect().contains(local_position)
