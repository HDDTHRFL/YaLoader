from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from yaloader.domain.download_speed_limit import format_download_speed_limit_label


class SpeedSettingsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.settings_button = QPushButton("Настройки", self)
        self.speed_limit_label = QLabel(self)

        self._configure_widgets()
        self._build_layout()

    def set_download_speed_limit(self, *, bytes_per_second: int | None) -> None:
        label = format_download_speed_limit_label(bytes_per_second=bytes_per_second)
        text = f"Скорость: {label}"
        self.speed_limit_label.setText(text)
        self.speed_limit_label.setToolTip(text)

    def _configure_widgets(self) -> None:
        self.settings_button.setObjectName("TinyGhostButton")
        self.settings_button.setToolTip("Открыть настройки загрузки")
        self.speed_limit_label.setObjectName("MutedLabel")

    def _build_layout(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(10)

        root_layout.addWidget(self.settings_button)
        root_layout.addWidget(self.speed_limit_label)
        root_layout.addStretch(1)
