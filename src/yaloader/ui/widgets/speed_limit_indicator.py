from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from yaloader.domain.download_speed_limit import format_download_speed_limit_label

SPEED_LIMIT_INDICATOR_EXPANDED_HEIGHT = 28


class SpeedLimitIndicatorPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._label = QLabel(self)

        self._configure_widgets()
        self._build_layout()

    def set_download_speed_limit(self, *, bytes_per_second: int | None) -> None:
        if bytes_per_second is None:
            self._label.clear()
            return

        speed_limit_label = format_download_speed_limit_label(bytes_per_second=bytes_per_second)
        text = f"Ограничение скорости загрузки: {speed_limit_label}"

        self._label.setText(text)
        self._label.setToolTip(text)

    def set_visible_height(self, *, height: int) -> None:
        normalized_height = max(0, min(SPEED_LIMIT_INDICATOR_EXPANDED_HEIGHT, height))
        self.setMinimumHeight(normalized_height)
        self.setMaximumHeight(normalized_height)

        if normalized_height > 0 and not self.isVisible():
            self.show()

    def set_expanded(self) -> None:
        self.set_visible_height(height=SPEED_LIMIT_INDICATOR_EXPANDED_HEIGHT)
        self.show()

    def set_collapsed(self) -> None:
        self.set_visible_height(height=0)
        self.hide()

    def current_visible_height(self) -> int:
        if not self.isVisible():
            return 0

        return max(0, min(SPEED_LIMIT_INDICATOR_EXPANDED_HEIGHT, self.maximumHeight()))

    def is_expanded(self) -> bool:
        return self.isVisible() and self.current_visible_height() > 0

    def _configure_widgets(self) -> None:
        self.setObjectName("SpeedLimitIndicatorPanel")
        self._label.setObjectName("SpeedLimitLabel")
        self.set_collapsed()

    def _build_layout(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(18, 9, 18, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._label)
        root_layout.addStretch(1)
