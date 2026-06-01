from __future__ import annotations

from pathlib import Path
from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from yaloader.domain.download_speed_limit import (
    DOWNLOAD_SPEED_LIMIT_PRESETS_BYTES,
    format_download_speed_limit_label,
)


class SettingsPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.downloads_dir_label = QLabel(self)
        self.download_speed_limit_label = QLabel("Ограничение скорости", self)
        self.download_speed_limit_combo_box = QComboBox(self)
        self.choose_downloads_dir_button = QPushButton("Выбрать папку", self)

        self._configure_widgets()
        self._build_layout()

    def set_downloads_dir(self, downloads_dir: Path) -> None:
        self.downloads_dir_label.setText(f"Папка загрузок: {downloads_dir}")
        self.downloads_dir_label.setToolTip(str(downloads_dir))

    def set_download_speed_limit(self, *, bytes_per_second: int | None) -> None:
        was_blocked = self.download_speed_limit_combo_box.blockSignals(True)

        try:
            option_index = self.download_speed_limit_combo_box.findData(bytes_per_second)

            if option_index < 0:
                option_index = 0

            self.download_speed_limit_combo_box.setCurrentIndex(option_index)
        finally:
            self.download_speed_limit_combo_box.blockSignals(was_blocked)

    def get_selected_download_speed_limit_bytes_per_second(self) -> int | None:
        return cast(int | None, self.download_speed_limit_combo_box.currentData())

    def _configure_widgets(self) -> None:
        self.setObjectName("PanelFrame")

        self.downloads_dir_label.setObjectName("MutedLabel")
        self.downloads_dir_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.download_speed_limit_label.setObjectName("FieldLabel")

        self.choose_downloads_dir_button.setObjectName("SecondaryButton")

        self.download_speed_limit_combo_box.setToolTip(
            "Максимальная скорость загрузки для новых задач в очереди"
        )

        for bytes_per_second in DOWNLOAD_SPEED_LIMIT_PRESETS_BYTES:
            self.download_speed_limit_combo_box.addItem(
                format_download_speed_limit_label(bytes_per_second=bytes_per_second),
                bytes_per_second,
            )

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(10)

        downloads_layout = QHBoxLayout()
        downloads_layout.setContentsMargins(0, 0, 0, 0)
        downloads_layout.setSpacing(12)
        downloads_layout.addWidget(self.downloads_dir_label, stretch=1)
        downloads_layout.addWidget(self.choose_downloads_dir_button)

        speed_limit_layout = QHBoxLayout()
        speed_limit_layout.setContentsMargins(0, 0, 0, 0)
        speed_limit_layout.setSpacing(12)
        speed_limit_layout.addWidget(self.download_speed_limit_label)
        speed_limit_layout.addWidget(self.download_speed_limit_combo_box)
        speed_limit_layout.addStretch(1)

        root_layout.addLayout(downloads_layout)
        root_layout.addLayout(speed_limit_layout)
