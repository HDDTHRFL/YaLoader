from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from yaloader.domain.download_speed_limit import (
    MAX_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
    MIN_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
    build_download_speed_limit_from_megabytes,
    convert_download_speed_limit_to_megabytes,
    format_download_speed_limit_label,
)

DIALOG_WIDTH = 460


class SpeedSettingsDialog(QDialog):
    download_speed_limit_changed = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._slider = QSlider(Qt.Orientation.Horizontal, self)
        self._spin_box = QSpinBox(self)
        self._current_value_label = QLabel(self)
        self._close_button = QPushButton("Закрыть", self)

        self._configure_widgets()
        self._connect_signals()
        self._build_layout()

    def set_download_speed_limit(self, *, bytes_per_second: int | None) -> None:
        megabytes_per_second = convert_download_speed_limit_to_megabytes(
            bytes_per_second=bytes_per_second,
        )
        self._set_value_without_signal(megabytes_per_second=megabytes_per_second)
        self._update_current_value_label(megabytes_per_second=megabytes_per_second)

    def _configure_widgets(self) -> None:
        self.setObjectName("SpeedSettingsDialog")
        self.setWindowTitle("Настройки загрузки")
        self.setModal(False)
        self.setMinimumWidth(DIALOG_WIDTH)

        self._slider.setObjectName("SpeedLimitSlider")
        self._slider.setRange(
            MIN_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
            MAX_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
        )
        self._slider.setSingleStep(1)
        self._slider.setPageStep(5)
        self._slider.setTickInterval(10)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)

        self._spin_box.setObjectName("SpeedLimitSpinBox")
        self._spin_box.setRange(
            MIN_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
            MAX_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
        )
        self._spin_box.setSpecialValueText("Без ограничения")
        self._spin_box.setSuffix(" MB/s")

        self._current_value_label.setObjectName("MutedLabel")
        self._close_button.setObjectName("SecondaryButton")

    def _connect_signals(self) -> None:
        self._slider.valueChanged.connect(self._handle_slider_value_changed)
        self._spin_box.valueChanged.connect(self._handle_spin_box_value_changed)
        self._close_button.clicked.connect(self.close)

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        title_label = QLabel("Ограничение скорости", self)
        title_label.setObjectName("SectionTitleLabel")

        description_label = QLabel(
            "0 означает отсутствие ограничения. Значения 1-100 задаются в MB/s.",
            self,
        )
        description_label.setObjectName("MutedLabel")
        description_label.setWordWrap(True)

        value_layout = QHBoxLayout()
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(12)
        value_layout.addWidget(self._spin_box)
        value_layout.addWidget(self._current_value_label, stretch=1)

        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.addStretch(1)
        actions_layout.addWidget(self._close_button)

        root_layout.addWidget(title_label)
        root_layout.addWidget(description_label)
        root_layout.addWidget(self._slider)
        root_layout.addLayout(value_layout)
        root_layout.addLayout(actions_layout)

    def _handle_slider_value_changed(self, value: int) -> None:
        self._set_spin_box_value_without_signal(value=value)
        self._emit_speed_limit_change(megabytes_per_second=value)

    def _handle_spin_box_value_changed(self, value: int) -> None:
        self._set_slider_value_without_signal(value=value)
        self._emit_speed_limit_change(megabytes_per_second=value)

    def _emit_speed_limit_change(self, *, megabytes_per_second: int) -> None:
        bytes_per_second = build_download_speed_limit_from_megabytes(
            megabytes_per_second=megabytes_per_second,
        )
        self._update_current_value_label(megabytes_per_second=megabytes_per_second)
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

    def _update_current_value_label(self, *, megabytes_per_second: int) -> None:
        bytes_per_second = build_download_speed_limit_from_megabytes(
            megabytes_per_second=megabytes_per_second,
        )
        self._current_value_label.setText(
            format_download_speed_limit_label(bytes_per_second=bytes_per_second),
        )


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
