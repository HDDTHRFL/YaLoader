from __future__ import annotations

from typing import override

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QRect,
    QSignalBlocker,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QEnterEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.app_settings import AppSettings
from yaloader.domain.download_speed_limit import (
    MAX_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
    MIN_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
    build_download_speed_limit_from_megabytes,
    convert_download_speed_limit_to_megabytes,
)

POPUP_WIDTH = 410
POPUP_SHOW_ANIMATION_DURATION_MS = 145
POPUP_RIGHT_EDGE_SHIFT_LEFT = -15
RESET_BUTTON_SIZE = 28
WINDOW_MAXIMUM_HEIGHT = 16_777_215


class SpeedLimitSlider(QSlider):
    interaction_state_changed = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)

        self.setProperty("hovered", "false")
        self.setProperty("pressed", "false")

    @override
    def enterEvent(self, event: QEnterEvent | None) -> None:
        self._set_hovered(is_hovered=True)
        super().enterEvent(event)

    @override
    def leaveEvent(self, event: QEvent | None) -> None:
        self._set_hovered(is_hovered=False)
        super().leaveEvent(event)

    @override
    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        self._set_pressed(is_pressed=True)
        super().mousePressEvent(event)

    @override
    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        super().mouseReleaseEvent(event)
        self._set_pressed(is_pressed=False)

    def _set_hovered(self, *, is_hovered: bool) -> None:
        next_value = "true" if is_hovered else "false"

        if self.property("hovered") == next_value:
            return

        self.setProperty("hovered", next_value)
        self._refresh_style()

    def _set_pressed(self, *, is_pressed: bool) -> None:
        next_value = "true" if is_pressed else "false"

        if self.property("pressed") == next_value:
            return

        self.setProperty("pressed", next_value)
        self._refresh_style()
        self.interaction_state_changed.emit(is_pressed)

    def _refresh_style(self) -> None:
        style = self.style()

        if isinstance(style, QStyle):
            style.unpolish(self)
            style.polish(self)


class SpeedSettingsDialog(QDialog):
    download_speed_limit_changed = pyqtSignal(object)
    show_history_on_startup_changed = pyqtSignal(bool)
    open_downloads_dir_after_queue_completed_changed = pyqtSignal(bool)
    confirm_clear_queue_changed = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._slider = SpeedLimitSlider(self)
        self._spin_box = QSpinBox(self)
        self._reset_button = QPushButton("↻", self)
        self._show_history_on_startup_checkbox = QCheckBox(
            "Показывать историю при запуске",
            self,
        )
        self._open_downloads_dir_after_queue_completed_checkbox = QCheckBox(
            "Открывать папку загрузок после завершения очереди",
            self,
        )
        self._confirm_clear_queue_checkbox = QCheckBox(
            "Спрашивать подтверждение перед очисткой очереди",
            self,
        )
        self._show_animation: QParallelAnimationGroup | None = None
        self._final_popup_height = 0

        self._configure_widgets()
        self._connect_signals()
        self._build_layout()

    def toggle_near_anchor(
        self,
        *,
        anchor_widget: QWidget,
        bytes_per_second: int | None,
        settings: AppSettings,
    ) -> None:
        if self.isVisible():
            self.close()
            return

        self.set_download_speed_limit(bytes_per_second=bytes_per_second)
        self.set_preferences(settings=settings)
        self._show_near_anchor(anchor_widget=anchor_widget)

    def set_download_speed_limit(self, *, bytes_per_second: int | None) -> None:
        megabytes_per_second = convert_download_speed_limit_to_megabytes(
            bytes_per_second=bytes_per_second,
        )
        self._set_value_without_signal(megabytes_per_second=megabytes_per_second)

    def set_preferences(self, *, settings: AppSettings) -> None:
        blockers = (
            QSignalBlocker(self._show_history_on_startup_checkbox),
            QSignalBlocker(self._open_downloads_dir_after_queue_completed_checkbox),
            QSignalBlocker(self._confirm_clear_queue_checkbox),
        )

        try:
            self._show_history_on_startup_checkbox.setChecked(settings.show_history_on_startup)
            self._open_downloads_dir_after_queue_completed_checkbox.setChecked(
                settings.open_downloads_dir_after_queue_completed,
            )
            self._confirm_clear_queue_checkbox.setChecked(settings.confirm_clear_queue)
        finally:
            del blockers

    def _configure_widgets(self) -> None:
        self.setObjectName("SpeedSettingsDialog")
        self.setWindowTitle("Настройки загрузки")
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setModal(False)
        self.setFixedWidth(POPUP_WIDTH)

        self._slider.setObjectName("SpeedLimitSlider")
        self._slider.setRange(
            MIN_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
            MAX_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
        )
        self._slider.setSingleStep(1)
        self._slider.setPageStep(5)
        self._slider.setTickPosition(QSlider.TickPosition.NoTicks)

        self._spin_box.setObjectName("SpeedLimitSpinBox")
        self._spin_box.setProperty("sliderPressed", "false")
        self._spin_box.setRange(
            MIN_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
            MAX_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
        )
        self._spin_box.setSpecialValueText("Без ограничения")
        self._spin_box.setSuffix(" MBytes/s")

        self._reset_button.setObjectName("SpeedResetButton")
        self._reset_button.setFixedSize(RESET_BUTTON_SIZE, RESET_BUTTON_SIZE)
        self._reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_button.setToolTip("Сбросить ограничение скорости")

        for checkbox in (
            self._show_history_on_startup_checkbox,
            self._open_downloads_dir_after_queue_completed_checkbox,
            self._confirm_clear_queue_checkbox,
        ):
            checkbox.setObjectName("SettingsCheckBox")
            checkbox.setCursor(Qt.CursorShape.PointingHandCursor)

    def _connect_signals(self) -> None:
        self._slider.valueChanged.connect(self._handle_slider_value_changed)
        self._slider.interaction_state_changed.connect(
            self._handle_slider_interaction_state_changed
        )
        self._spin_box.valueChanged.connect(self._handle_spin_box_value_changed)
        self._reset_button.clicked.connect(self._handle_reset_button_clicked)

        self._show_history_on_startup_checkbox.toggled.connect(
            self.show_history_on_startup_changed.emit,
        )
        self._open_downloads_dir_after_queue_completed_checkbox.toggled.connect(
            self.open_downloads_dir_after_queue_completed_changed.emit,
        )
        self._confirm_clear_queue_checkbox.toggled.connect(
            self.confirm_clear_queue_changed.emit,
        )

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(10)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        title_label = QLabel("Ограничение скорости загрузки", self)
        title_label.setObjectName("SpeedSettingsPopupTitle")

        behavior_title_label = QLabel("Поведение приложения", self)
        behavior_title_label.setObjectName("SmallSectionTitleLabel")

        title_layout.addWidget(title_label)
        title_layout.addStretch(1)
        title_layout.addWidget(self._reset_button)

        root_layout.addLayout(title_layout)
        root_layout.addWidget(self._slider)
        root_layout.addWidget(self._spin_box)
        root_layout.addWidget(behavior_title_label)
        root_layout.addWidget(self._show_history_on_startup_checkbox)
        root_layout.addWidget(self._open_downloads_dir_after_queue_completed_checkbox)
        root_layout.addWidget(self._confirm_clear_queue_checkbox)

    def _show_near_anchor(self, *, anchor_widget: QWidget) -> None:
        self.setMinimumHeight(0)
        self.setMaximumHeight(WINDOW_MAXIMUM_HEIGHT)
        self.adjustSize()

        final_width = self.sizeHint().width()
        final_height = self.sizeHint().height()
        self._final_popup_height = final_height

        anchor_left_bottom = anchor_widget.mapToGlobal(anchor_widget.rect().bottomLeft())
        final_right = anchor_left_bottom.x() - POPUP_RIGHT_EDGE_SHIFT_LEFT
        final_top = anchor_left_bottom.y()

        final_geometry = QRect(
            final_right - final_width + 1,
            final_top,
            final_width,
            final_height,
        )

        self._start_show_animation(final_geometry=final_geometry)

    def _start_show_animation(self, *, final_geometry: QRect) -> None:
        if self._show_animation is not None:
            self._show_animation.stop()

        start_height = 1
        final_height = max(1, final_geometry.height())

        self.setWindowOpacity(0.0)
        self.setGeometry(
            final_geometry.left(),
            final_geometry.top(),
            final_geometry.width(),
            start_height,
        )
        self.setMinimumHeight(start_height)
        self.setMaximumHeight(start_height)
        self.show()
        self.raise_()
        self.activateWindow()

        minimum_height_animation = QPropertyAnimation(self, b"minimumHeight", self)
        minimum_height_animation.setDuration(POPUP_SHOW_ANIMATION_DURATION_MS)
        minimum_height_animation.setStartValue(start_height)
        minimum_height_animation.setEndValue(final_height)
        minimum_height_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        maximum_height_animation = QPropertyAnimation(self, b"maximumHeight", self)
        maximum_height_animation.setDuration(POPUP_SHOW_ANIMATION_DURATION_MS)
        maximum_height_animation.setStartValue(start_height)
        maximum_height_animation.setEndValue(final_height)
        maximum_height_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        opacity_animation = QPropertyAnimation(self, b"windowOpacity", self)
        opacity_animation.setDuration(POPUP_SHOW_ANIMATION_DURATION_MS)
        opacity_animation.setStartValue(0.0)
        opacity_animation.setEndValue(1.0)
        opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        animation_group = QParallelAnimationGroup(self)
        animation_group.addAnimation(minimum_height_animation)
        animation_group.addAnimation(maximum_height_animation)
        animation_group.addAnimation(opacity_animation)
        animation_group.finished.connect(self._handle_show_animation_finished)
        animation_group.start()

        self._show_animation = animation_group

    def _handle_show_animation_finished(self) -> None:
        final_height = max(1, self._final_popup_height)

        self.setMinimumHeight(final_height)
        self.setMaximumHeight(final_height)
        self._show_animation = None

    def _handle_slider_value_changed(self, value: int) -> None:
        self._set_spin_box_value_without_signal(value=value)
        self._emit_speed_limit_change(megabytes_per_second=value)

    def _handle_slider_interaction_state_changed(self, is_pressed: bool) -> None:
        self._spin_box.setProperty("sliderPressed", "true" if is_pressed else "false")
        self._refresh_spin_box_style()

    def _handle_spin_box_value_changed(self, value: int) -> None:
        self._set_slider_value_without_signal(value=value)
        self._emit_speed_limit_change(megabytes_per_second=value)

    def _handle_reset_button_clicked(self, _checked: bool = False) -> None:
        self._set_value_without_signal(megabytes_per_second=MIN_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB)
        self._emit_speed_limit_change(
            megabytes_per_second=MIN_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
        )

    def _emit_speed_limit_change(self, *, megabytes_per_second: int) -> None:
        bytes_per_second = build_download_speed_limit_from_megabytes(
            megabytes_per_second=megabytes_per_second,
        )
        self.download_speed_limit_changed.emit(bytes_per_second)

    def _set_value_without_signal(self, *, megabytes_per_second: int) -> None:
        self._set_slider_value_without_signal(value=megabytes_per_second)
        self._set_spin_box_value_without_signal(value=megabytes_per_second)

    def _set_slider_value_without_signal(self, *, value: int) -> None:
        blocker = QSignalBlocker(self._slider)
        self._slider.setValue(value)
        del blocker

    def _set_spin_box_value_without_signal(self, *, value: int) -> None:
        blocker = QSignalBlocker(self._spin_box)
        self._spin_box.setValue(value)
        del blocker

    def _refresh_spin_box_style(self) -> None:
        style = self._spin_box.style()

        if isinstance(style, QStyle):
            style.unpolish(self._spin_box)
            style.polish(self._spin_box)


def normalize_download_speed_limit_signal_value(value: object) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool):
        message = "Download speed limit signal value must be an integer or None."
        raise ValueError(message)

    if isinstance(value, int):
        return value

    message = "Download speed limit signal value must be an integer or None."
    raise ValueError(message)
