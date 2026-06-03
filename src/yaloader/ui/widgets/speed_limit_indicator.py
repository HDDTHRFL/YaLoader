from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from yaloader.domain.download_speed_limit import format_download_speed_limit_label


class SpeedLimitIndicatorPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._label = QLabel(self)

        self._configure_widgets()
        self._build_layout()

    def set_download_speed_limit(self, *, bytes_per_second: int | None) -> None:
        if bytes_per_second is None:
            self._label.clear()
            self.hide()
            return

        speed_limit_label = format_download_speed_limit_label(bytes_per_second=bytes_per_second)
        text = f"Ограничение скорости: {speed_limit_label}"

        self._label.setText(text)
        self._label.setToolTip(text)
        self.show()

    def _configure_widgets(self) -> None:
        self.setObjectName("SpeedLimitIndicatorPanel")
        self._label.setObjectName("SpeedLimitLabel")
        self.hide()

    def _build_layout(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(18, 9, 18, 9)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._label)
        root_layout.addStretch(1)
