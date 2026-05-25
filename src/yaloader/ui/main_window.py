from __future__ import annotations

from typing import cast

from pydantic import ValidationError
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.config.app_info import APP_DISPLAY_NAME
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import OutputFormat, VideoQuality
from yaloader.domain.format_rules import get_download_mode_for_output_format
from yaloader.services.app_container import AppContainer

MODE_COLUMN_WIDTH = 72
URL_COLUMN_WIDTH = 420
QUALITY_COLUMN_WIDTH = 96
FORMAT_COLUMN_WIDTH = 76
STATUS_COLUMN_WIDTH = 96
FOLDER_COLUMN_WIDTH = 260


class MainWindow(QMainWindow):
    def __init__(self, container: AppContainer) -> None:
        super().__init__()

        self._container = container
        self._url_input = QLineEdit(self)
        self._quality_combo_box = QComboBox(self)
        self._format_combo_box = QComboBox(self)
        self._download_button = QPushButton("Добавить в очередь", self)
        self._queue_table = QTableWidget(self)
        self._status_label = QLabel("Готов к работе", self)

        self._configure_window()
        self._configure_widgets()
        self._connect_signals()
        self.setCentralWidget(self._build_central_widget())

    def _configure_window(self) -> None:
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(980, 620)
        self.setMinimumSize(860, 520)

    def _configure_widgets(self) -> None:
        self._url_input.setPlaceholderText("Вставьте ссылку на YouTube, Shorts или плейлист")
        self._url_input.setClearButtonEnabled(True)

        for quality in VideoQuality:
            self._quality_combo_box.addItem(quality.value, quality)

        for output_format in OutputFormat:
            self._format_combo_box.addItem(output_format.value, output_format)

        self._configure_queue_table()

        self._status_label.setObjectName("StatusLabel")
        self._status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    def _configure_queue_table(self) -> None:
        self._queue_table.setColumnCount(6)
        self._queue_table.setHorizontalHeaderLabels(
            [
                "Режим",
                "Ссылка",
                "Качество",
                "Формат",
                "Статус",
                "Папка",
            ]
        )
        self._queue_table.setAlternatingRowColors(True)
        self._queue_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._queue_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._queue_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self._queue_table.setColumnWidth(0, MODE_COLUMN_WIDTH)
        self._queue_table.setColumnWidth(1, URL_COLUMN_WIDTH)
        self._queue_table.setColumnWidth(2, QUALITY_COLUMN_WIDTH)
        self._queue_table.setColumnWidth(3, FORMAT_COLUMN_WIDTH)
        self._queue_table.setColumnWidth(4, STATUS_COLUMN_WIDTH)
        self._queue_table.setColumnWidth(5, FOLDER_COLUMN_WIDTH)

    def _connect_signals(self) -> None:
        self._download_button.clicked.connect(self._handle_add_to_queue_clicked)

    def _build_central_widget(self) -> QWidget:
        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(28, 24, 28, 24)
        root_layout.setSpacing(18)

        root_layout.addWidget(self._build_header())
        root_layout.addWidget(self._build_input_panel())
        root_layout.addWidget(self._build_queue_panel(), stretch=1)
        root_layout.addWidget(self._build_footer())

        return central_widget

    def _build_header(self) -> QWidget:
        header = QWidget(self)
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title_label = QLabel(APP_DISPLAY_NAME, header)
        title_label.setObjectName("TitleLabel")

        subtitle_label = QLabel(
            "Загрузка видео и аудио в максимальном доступном качестве",
            header,
        )
        subtitle_label.setObjectName("SubtitleLabel")

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        return header

    def _build_input_panel(self) -> QFrame:
        panel = QFrame(self)
        panel.setObjectName("PanelFrame")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        url_label = QLabel("Ссылка", panel)
        url_label.setObjectName("FieldLabel")

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        controls_layout.addWidget(self._url_input, stretch=1)
        controls_layout.addWidget(self._quality_combo_box)
        controls_layout.addWidget(self._format_combo_box)
        controls_layout.addWidget(self._download_button)

        layout.addWidget(url_label)
        layout.addLayout(controls_layout)

        return panel

    def _build_queue_panel(self) -> QFrame:
        panel = QFrame(self)
        panel.setObjectName("PanelFrame")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel("Очередь загрузок", panel)
        title_label.setObjectName("SectionTitleLabel")

        layout.addWidget(title_label)
        layout.addWidget(self._queue_table, stretch=1)

        return panel

    def _build_footer(self) -> QWidget:
        footer = QWidget(self)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(0, 0, 0, 0)

        downloads_dir_label = QLabel(
            f"Папка загрузок: {self._container.paths.downloads_dir}",
            footer,
        )
        downloads_dir_label.setObjectName("MutedLabel")
        downloads_dir_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addWidget(self._status_label)
        layout.addStretch(1)
        layout.addWidget(downloads_dir_label)

        return footer

    def _handle_add_to_queue_clicked(self) -> None:
        url = self._url_input.text().strip()

        if not url:
            self._status_label.setText("Сначала вставьте ссылку")
            return

        selected_output_format = self._get_selected_output_format()
        selected_video_quality = self._get_selected_video_quality()

        try:
            request = DownloadRequest(
                url=url,
                target_dir=self._container.paths.downloads_dir,
                mode=get_download_mode_for_output_format(output_format=selected_output_format),
                output_format=selected_output_format,
                video_quality=selected_video_quality,
            )
        except ValidationError as error:
            first_error_message = error.errors()[0]["msg"]
            self._status_label.setText(f"Некорректная задача загрузки: {first_error_message}")
            return

        task = self._container.download_queue_service.add_download(request=request)
        self._append_task_to_table(task=task)

        self._url_input.clear()
        self._status_label.setText(
            f"Добавлено в очередь: {self._container.download_queue_service.count()}"
        )

    def _get_selected_video_quality(self) -> VideoQuality:
        return cast(VideoQuality, self._quality_combo_box.currentData())

    def _get_selected_output_format(self) -> OutputFormat:
        return cast(OutputFormat, self._format_combo_box.currentData())

    def _append_task_to_table(self, task: DownloadTask) -> None:
        row_index = self._queue_table.rowCount()
        self._queue_table.insertRow(row_index)

        values = (
            task.mode.value,
            task.url.value,
            task.video_quality.value,
            task.output_format.value,
            task.status.value,
            str(task.target_dir),
        )

        for column_index, value in enumerate(values):
            table_item = QTableWidgetItem(value)
            table_item.setToolTip(value)
            self._queue_table.setItem(row_index, column_index, table_item)

        self._queue_table.resizeRowsToContents()
