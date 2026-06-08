from __future__ import annotations

from typing import cast, override

from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from yaloader.domain.enums import OutputFormat, VideoQuality
from yaloader.ui.widgets.common.url_drop_line_edit import (
    UrlDropLineEdit,
    extract_first_supported_media_url_from_drop_event,
)


class DownloadInputPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._is_add_to_queue_available = True

        self.url_input = UrlDropLineEdit(self)
        self.quality_combo_box = QComboBox(self)
        self.format_combo_box = QComboBox(self)
        self.add_to_queue_button = QPushButton("Добавить в очередь", self)

        self._configure_widgets()
        self._connect_signals()
        self._build_layout()
        self._sync_add_to_queue_button_state()

    def get_url_text(self) -> str:
        return self.url_input.text().strip()

    def clear_url(self) -> None:
        self.url_input.clear()
        self._sync_add_to_queue_button_state()

    def focus_url_input(self) -> None:
        self.url_input.setFocus()
        self.url_input.selectAll()

    def get_selected_video_quality(self) -> VideoQuality:
        return cast(VideoQuality, self.quality_combo_box.currentData())

    def get_selected_output_format(self) -> OutputFormat:
        return cast(OutputFormat, self.format_combo_box.currentData())

    def set_add_to_queue_available(self, *, is_available: bool) -> None:
        self._is_add_to_queue_available = is_available
        self._sync_add_to_queue_button_state()

    @override
    def dragEnterEvent(self, event: QDragEnterEvent | None) -> None:
        if self._accept_supported_url_drag_event(event=event):
            return

        super().dragEnterEvent(event)

    @override
    def dragMoveEvent(self, event: QDragMoveEvent | None) -> None:
        if self._accept_supported_url_drag_event(event=event):
            return

        super().dragMoveEvent(event)

    @override
    def dragLeaveEvent(self, event: QDragLeaveEvent | None) -> None:
        self.url_input.set_drop_highlight_active(is_active=False)
        super().dragLeaveEvent(event)

    @override
    def dropEvent(self, event: QDropEvent | None) -> None:
        self.url_input.set_drop_highlight_active(is_active=False)

        if event is None:
            return

        dropped_url = extract_first_supported_media_url_from_drop_event(event=event)

        if dropped_url is None:
            super().dropEvent(event)
            return

        self.url_input.setText(dropped_url)
        self.url_input.setFocus()
        self.url_input.setCursorPosition(len(dropped_url))
        self._sync_add_to_queue_button_state()

        event.acceptProposedAction()

    def _configure_widgets(self) -> None:
        self.setObjectName("PanelFrame")
        self.setAcceptDrops(True)

        self.url_input.setPlaceholderText(
            "Вставьте ссылку YouTube на видео, Shorts или плейлист 👀"
        )
        self.url_input.setToolTip("Можно вставить ссылку вручную или перетащить её мышью")
        self.url_input.setClearButtonEnabled(True)

        for quality in VideoQuality:
            self.quality_combo_box.addItem(quality.value, quality)

        for output_format in OutputFormat:
            self.format_combo_box.addItem(output_format.value, output_format)

    def _connect_signals(self) -> None:
        self.url_input.returnPressed.connect(self._handle_url_input_return_pressed)
        self.url_input.textChanged.connect(self._handle_url_input_text_changed)

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

    def _handle_url_input_text_changed(self, _text: str) -> None:
        self._sync_add_to_queue_button_state()

    def _handle_url_input_return_pressed(self) -> None:
        if not self.add_to_queue_button.isEnabled():
            return

        self.add_to_queue_button.click()

    def _sync_add_to_queue_button_state(self) -> None:
        self.add_to_queue_button.setEnabled(
            self._is_add_to_queue_available and bool(self.get_url_text())
        )

    def _accept_supported_url_drag_event(
        self,
        *,
        event: QDragEnterEvent | QDragMoveEvent | None,
    ) -> bool:
        if event is None:
            self.url_input.set_drop_highlight_active(is_active=False)
            return False

        if extract_first_supported_media_url_from_drop_event(event=event) is None:
            self.url_input.set_drop_highlight_active(is_active=False)
            return False

        self.url_input.set_drop_highlight_active(is_active=True)
        event.acceptProposedAction()
        return True
