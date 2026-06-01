from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QTimer
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QLabel

from yaloader.ui.status_messages import (
    DEFAULT_STATUS_MESSAGE,
    TRANSIENT_STATUS_MESSAGE_BLINK_DURATION_MS,
    TRANSIENT_STATUS_MESSAGE_DURATION_MS,
    TRANSIENT_STATUS_MESSAGE_MIN_OPACITY,
)


class FooterStatusPresenter:
    def __init__(self, *, label: QLabel, parent: QObject) -> None:
        self._label = label
        self._default_status_message = DEFAULT_STATUS_MESSAGE
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

        self._label.setText(message)
        self._start_blink_animation()
        self._reset_timer.start()

    def shutdown(self) -> None:
        self._reset_timer.stop()
        self._stop_blink_animation()

    def _configure_timer(self) -> None:
        self._reset_timer.setSingleShot(True)
        self._reset_timer.setInterval(TRANSIENT_STATUS_MESSAGE_DURATION_MS)
        self._reset_timer.timeout.connect(self._restore_default_status_message)

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

    def _restore_default_status_message(self) -> None:
        self._stop_blink_animation()
        self._label.setText(self._default_status_message)

    def _start_blink_animation(self) -> None:
        self._blink_animation.stop()
        self._opacity_effect.setOpacity(1.0)
        self._blink_animation.start()

    def _stop_blink_animation(self) -> None:
        self._blink_animation.stop()
        self._opacity_effect.setOpacity(1.0)
