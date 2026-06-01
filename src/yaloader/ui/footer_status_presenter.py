from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QTimer
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QLabel

from yaloader.ui.status_messages import (
    DEFAULT_STATUS_MESSAGE,
    TRANSIENT_STATUS_MESSAGE_BLINK_DURATION_MS,
    TRANSIENT_STATUS_MESSAGE_DURATION_MS,
    TRANSIENT_STATUS_MESSAGE_MIN_OPACITY,
    TRANSIENT_STATUS_MESSAGE_RESTORE_OPACITY_THRESHOLD,
)


class FooterStatusPresenter:
    def __init__(self, *, label: QLabel, parent: QObject) -> None:
        self._label = label
        self._default_status_message = DEFAULT_STATUS_MESSAGE
        self._is_default_restore_pending = False

        self._reset_timer = QTimer(parent)
        self._opacity_effect = QGraphicsOpacityEffect(label)
        self._blink_animation = QPropertyAnimation(
            self._opacity_effect,
            b"opacity",
            parent,
        )

        self._configure_timer()
        self._configure_animation()

    def show_primary(self, *, message: str) -> None:
        self._reset_timer.stop()
        self._is_default_restore_pending = False
        self._stop_blink_animation()

        self._default_status_message = message
        self._label.setText(message)

    def show_transient(
        self,
        *,
        message: str,
        fallback_status_message: str | None = None,
    ) -> None:
        if fallback_status_message is not None:
            self._default_status_message = fallback_status_message

        self._is_default_restore_pending = False
        self._label.setText(message)
        self._start_blink_animation()
        self._reset_timer.start()

    def shutdown(self) -> None:
        self._reset_timer.stop()
        self._is_default_restore_pending = False
        self._stop_blink_animation()

    def _configure_timer(self) -> None:
        self._reset_timer.setSingleShot(True)
        self._reset_timer.setInterval(TRANSIENT_STATUS_MESSAGE_DURATION_MS)
        self._reset_timer.timeout.connect(self._request_default_status_message_restore)

    def _configure_animation(self) -> None:
        self._opacity_effect.setOpacity(1.0)
        self._label.setGraphicsEffect(self._opacity_effect)

        self._blink_animation.setDuration(TRANSIENT_STATUS_MESSAGE_BLINK_DURATION_MS)
        self._blink_animation.setStartValue(1.0)
        self._blink_animation.setKeyValueAt(
            0.5,
            TRANSIENT_STATUS_MESSAGE_MIN_OPACITY,
        )
        self._blink_animation.setEndValue(1.0)
        self._blink_animation.setLoopCount(-1)
        self._blink_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._blink_animation.valueChanged.connect(self._handle_blink_opacity_changed)

    def _request_default_status_message_restore(self) -> None:
        self._is_default_restore_pending = True
        self._restore_default_status_message_if_opacity_is_low(
            opacity=self._opacity_effect.opacity(),
        )

    def _handle_blink_opacity_changed(self, value: object) -> None:
        if not self._is_default_restore_pending:
            return

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return

        self._restore_default_status_message_if_opacity_is_low(opacity=float(value))

    def _restore_default_status_message_if_opacity_is_low(self, *, opacity: float) -> None:
        if opacity > TRANSIENT_STATUS_MESSAGE_RESTORE_OPACITY_THRESHOLD:
            return

        self._restore_default_status_message()

    def _restore_default_status_message(self) -> None:
        self._is_default_restore_pending = False
        self._stop_blink_animation()
        self._label.setText(self._default_status_message)

    def _start_blink_animation(self) -> None:
        self._blink_animation.stop()
        self._opacity_effect.setOpacity(1.0)
        self._blink_animation.start()

    def _stop_blink_animation(self) -> None:
        self._blink_animation.stop()
        self._opacity_effect.setOpacity(1.0)
