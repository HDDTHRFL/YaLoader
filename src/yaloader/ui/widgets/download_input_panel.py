from __future__ import annotations

from typing import cast

from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from yaloader.domain.enums import OutputFormat, VideoQuality


class DownloadInputPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.url_input = QLineEdit(self)
        self.quality_combo_box = QComboBox(self)
        self.format_combo_box = QComboBox(self)
        self.add_to_queue_button = QPushButton("Добавить в очередь", self)

        self._configure_widgets()
        self._connect_signals()
        self._build_layout()

    def get_url_text(self) -> str:
        return self.url_input.text().strip()

    def clear_url(self) -> None:
        self.url_input.clear()

    def focus_url_input(self) -> None:
        self.url_input.setFocus()
        self.url_input.selectAll()

    def get_selected_video_quality(self) -> VideoQuality:
        return cast(VideoQuality, self.quality_combo_box.currentData())

    def get_selected_output_format(self) -> OutputFormat:
        return cast(OutputFormat, self.format_combo_box.currentData())

    def _configure_widgets(self) -> None:
        self.setObjectName("PanelFrame")

        self.url_input.setPlaceholderText("Вставьте ссылку на YouTube, Shorts или плейлист")
        self.url_input.setClearButtonEnabled(True)

        for quality in VideoQuality:
            self.quality_combo_box.addItem(quality.value, quality)

        for output_format in OutputFormat:
            self.format_combo_box.addItem(output_format.value, output_format)

    def _connect_signals(self) -> None:
        self.url_input.returnPressed.connect(self.add_to_queue_button.click)

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        url_label = QLabel("Ссылка", self)
        url_label.setObjectName("FieldLabel")

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        controls_layout.addWidget(self.url_input, stretch=1)
        controls_layout.addWidget(self.quality_combo_box)
        controls_layout.addWidget(self.format_combo_box)
        controls_layout.addWidget(self.add_to_queue_button)

        layout.addWidget(url_label)
        layout.addLayout(controls_layout)
