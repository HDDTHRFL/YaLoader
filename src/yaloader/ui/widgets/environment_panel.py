from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QStyle, QVBoxLayout, QWidget

from yaloader.application.dto.environment_status import EnvironmentItemStatus, EnvironmentStatus


class EnvironmentPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.refresh_button = QPushButton("Обновить", self)
        self.open_cookies_dir_button = QPushButton("Cookies", self)
        self.open_downloads_dir_button = QPushButton("Загрузки", self)

        self._ffmpeg_status_label = QLabel(self)
        self._deno_status_label = QLabel(self)
        self._ytdlp_status_label = QLabel(self)
        self._cookies_status_label = QLabel(self)
        self._downloads_dir_status_label = QLabel(self)

        self._configure_widgets()
        self._build_layout()

    def set_status(self, status: EnvironmentStatus) -> None:
        self._set_item_status(self._ffmpeg_status_label, status.ffmpeg)
        self._set_item_status(self._deno_status_label, status.deno)
        self._set_item_status(self._ytdlp_status_label, status.ytdlp)
        self._set_item_status(self._cookies_status_label, status.cookies)
        self._set_item_status(self._downloads_dir_status_label, status.downloads_dir)

    def _configure_widgets(self) -> None:
        self.setObjectName("EnvironmentPanel")

        for label in self._status_labels:
            label.setObjectName("StatusChip")
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        for button in (
            self.refresh_button,
            self.open_cookies_dir_button,
            self.open_downloads_dir_button,
        ):
            button.setObjectName("GhostButton")

        self.open_cookies_dir_button.setToolTip("Открыть папку с cookies.txt")
        self.open_downloads_dir_button.setToolTip("Открыть папку загрузок")
        self.refresh_button.setToolTip("Повторно проверить состояние системы")

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 12, 18, 12)
        root_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title_label = QLabel("Состояние системы", self)
        title_label.setObjectName("SmallSectionTitleLabel")

        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.refresh_button)
        header_layout.addWidget(self.open_cookies_dir_button)
        header_layout.addWidget(self.open_downloads_dir_button)

        chips_layout = QHBoxLayout()
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(8)

        for label in self._status_labels:
            chips_layout.addWidget(label)

        chips_layout.addStretch(1)

        root_layout.addLayout(header_layout)
        root_layout.addLayout(chips_layout)

    @property
    def _status_labels(self) -> tuple[QLabel, ...]:
        return (
            self._ffmpeg_status_label,
            self._deno_status_label,
            self._ytdlp_status_label,
            self._cookies_status_label,
            self._downloads_dir_status_label,
        )

    def _set_item_status(self, label: QLabel, status: EnvironmentItemStatus) -> None:
        marker = "●"
        label.setProperty("state", "ok" if status.is_ok else "warning")
        label.setText(f"{marker} {status.title}: {status.message}")

        style = label.style()

        if isinstance(style, QStyle):
            style.unpolish(label)
            style.polish(label)

        if status.path is not None:
            label.setToolTip(str(status.path))
        else:
            label.setToolTip(status.message)
