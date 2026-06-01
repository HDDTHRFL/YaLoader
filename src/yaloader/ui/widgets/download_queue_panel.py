from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from yaloader.ui.widgets.download_queue_table import DownloadQueueTable


class DownloadQueuePanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.queue_table = DownloadQueueTable(self)
        self.start_queue_button = QPushButton("Скачать очередь", self)
        self.remove_from_queue_button = QPushButton("Удалить выбранное", self)
        self.clear_queue_button = QPushButton("Очистить очередь", self)

        self._configure_widgets()
        self._build_layout()

    def _configure_widgets(self) -> None:
        self.setObjectName("PanelFrame")

        self.start_queue_button.setObjectName("PrimaryButton")
        self.remove_from_queue_button.setObjectName("SecondaryButton")
        self.clear_queue_button.setObjectName("SecondaryButton")

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel("Очередь загрузок", self)
        title_label.setObjectName("SectionTitleLabel")

        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(12)
        actions_layout.addWidget(self.remove_from_queue_button)
        actions_layout.addWidget(self.clear_queue_button)
        actions_layout.addStretch(1)
        actions_layout.addWidget(self.start_queue_button)

        layout.addWidget(title_label)
        layout.addWidget(self.queue_table, stretch=1)
        layout.addLayout(actions_layout)
