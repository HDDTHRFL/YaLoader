from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import cast, override
from uuid import UUID

from pydantic import ValidationError
from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QCloseEvent, QResizeEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.services.download_queue_service import is_downloadable
from yaloader.config.app_info import APP_DISPLAY_NAME
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus, OutputFormat, VideoQuality
from yaloader.domain.format_rules import get_download_mode_for_output_format
from yaloader.services.app_container import AppContainer

WINDOW_INITIAL_WIDTH = 1180
WINDOW_INITIAL_HEIGHT = 850
WINDOW_MINIMUM_WIDTH = 1040
WINDOW_MINIMUM_HEIGHT = 680

DOWNLOAD_WORKERS_COUNT = 1
DOWNLOAD_POLL_INTERVAL_MS = 250

MODE_COLUMN_INDEX = 0
URL_COLUMN_INDEX = 1
QUALITY_COLUMN_INDEX = 2
FORMAT_COLUMN_INDEX = 3
STATUS_COLUMN_INDEX = 4
FOLDER_COLUMN_INDEX = 5

MIN_COLUMN_WIDTHS = {
    MODE_COLUMN_INDEX: 72,
    URL_COLUMN_INDEX: 320,
    QUALITY_COLUMN_INDEX: 96,
    FORMAT_COLUMN_INDEX: 76,
    STATUS_COLUMN_INDEX: 104,
    FOLDER_COLUMN_INDEX: 220,
}

COLUMN_STRETCH_WEIGHTS = {
    MODE_COLUMN_INDEX: 0.25,
    URL_COLUMN_INDEX: 6.0,
    QUALITY_COLUMN_INDEX: 0.35,
    FORMAT_COLUMN_INDEX: 0.35,
    STATUS_COLUMN_INDEX: 0.45,
    FOLDER_COLUMN_INDEX: 2.6,
}


class MainWindow(QMainWindow):
    def __init__(self, container: AppContainer) -> None:
        super().__init__()

        self._container = container
        self._settings = container.settings

        self._url_input = QLineEdit(self)
        self._quality_combo_box = QComboBox(self)
        self._format_combo_box = QComboBox(self)
        self._add_to_queue_button = QPushButton("Добавить в очередь", self)
        self._choose_downloads_dir_button = QPushButton("Выбрать папку", self)
        self._delete_cookies_button = QPushButton("Удалить cookies.txt", self)
        self._start_queue_button = QPushButton("Скачать очередь", self)
        self._remove_from_queue_button = QPushButton("Удалить выбранное", self)
        self._queue_table = QTableWidget(self)
        self._status_label = QLabel("Готов к работе", self)
        self._downloads_dir_label = QLabel(self)
        self._cookies_status_label = QLabel(self)

        self._task_ids_by_row: dict[int, UUID] = {}
        self._row_by_task_id: dict[UUID, int] = {}
        self._queued_download_task_ids: list[UUID] = []

        self._download_executor = ThreadPoolExecutor(
            max_workers=DOWNLOAD_WORKERS_COUNT,
            thread_name_prefix="yaloader-download",
        )
        self._active_download_future: Future[DownloadResult] | None = None
        self._active_download_task_id: UUID | None = None
        self._download_poll_timer = QTimer(self)

        self._configure_window()
        self._configure_widgets()
        self._connect_signals()
        self.setCentralWidget(self._build_central_widget())

        self._update_downloads_dir_label()
        self._update_cookies_status_label()
        self._resize_queue_columns()

    @override
    def closeEvent(self, event: QCloseEvent | None) -> None:
        self._download_poll_timer.stop()
        self._download_executor.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)

    @override
    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._resize_queue_columns()

    def _configure_window(self) -> None:
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(WINDOW_INITIAL_WIDTH, WINDOW_INITIAL_HEIGHT)
        self.setMinimumSize(WINDOW_MINIMUM_WIDTH, WINDOW_MINIMUM_HEIGHT)

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

        self._downloads_dir_label.setObjectName("MutedLabel")
        self._downloads_dir_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._cookies_status_label.setObjectName("MutedLabel")
        self._cookies_status_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._delete_cookies_button.setToolTip(str(self._container.paths.cookies_file))

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
        self._queue_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        vertical_header = cast(QHeaderView, self._queue_table.verticalHeader())
        vertical_header.hide()

        self._resize_queue_columns()

    def _connect_signals(self) -> None:
        self._add_to_queue_button.clicked.connect(self._handle_add_to_queue_clicked)
        self._start_queue_button.clicked.connect(self._handle_start_queue_clicked)
        self._remove_from_queue_button.clicked.connect(self._handle_remove_selected_task_clicked)
        self._choose_downloads_dir_button.clicked.connect(self._handle_choose_downloads_dir_clicked)
        self._delete_cookies_button.clicked.connect(self._handle_delete_cookies_clicked)
        self._download_poll_timer.timeout.connect(self._poll_download_result)
        self._queue_table.customContextMenuRequested.connect(self._show_queue_context_menu)

    def _build_central_widget(self) -> QWidget:
        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(28, 24, 28, 24)
        root_layout.setSpacing(18)

        root_layout.addWidget(self._build_header())
        root_layout.addWidget(self._build_input_panel())
        root_layout.addWidget(self._build_settings_panel())
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
        controls_layout.addWidget(self._add_to_queue_button)

        layout.addWidget(url_label)
        layout.addLayout(controls_layout)

        return panel

    def _build_settings_panel(self) -> QFrame:
        panel = QFrame(self)
        panel.setObjectName("PanelFrame")

        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        labels_layout = QVBoxLayout()
        labels_layout.setContentsMargins(0, 0, 0, 0)
        labels_layout.setSpacing(4)
        labels_layout.addWidget(self._downloads_dir_label)
        labels_layout.addWidget(self._cookies_status_label)

        layout.addLayout(labels_layout, stretch=1)
        layout.addWidget(self._choose_downloads_dir_button)
        layout.addWidget(self._delete_cookies_button)

        return panel

    def _build_queue_panel(self) -> QFrame:
        panel = QFrame(self)
        panel.setObjectName("PanelFrame")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel("Очередь загрузок", panel)
        title_label.setObjectName("SectionTitleLabel")

        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(12)
        actions_layout.addWidget(self._remove_from_queue_button)
        actions_layout.addStretch(1)
        actions_layout.addWidget(self._start_queue_button)

        layout.addWidget(title_label)
        layout.addWidget(self._queue_table, stretch=1)
        layout.addLayout(actions_layout)

        return panel

    def _build_footer(self) -> QWidget:
        footer = QWidget(self)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._status_label)
        layout.addStretch(1)

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
                target_dir=self._settings.downloads_dir,
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

    def _handle_choose_downloads_dir_clicked(self) -> None:
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для загрузок",
            str(self._settings.downloads_dir),
        )

        if not selected_dir:
            return

        downloads_dir = Path(selected_dir)
        downloads_dir.mkdir(parents=True, exist_ok=True)

        self._settings = self._container.settings_service.update_downloads_dir(
            downloads_dir=downloads_dir,
        )
        self._update_downloads_dir_label()
        self._status_label.setText(f"Папка загрузок изменена: {downloads_dir}")

    def _handle_delete_cookies_clicked(self) -> None:
        cookies_file = self._container.paths.cookies_file

        if not cookies_file.is_file():
            self._status_label.setText(f"cookies.txt не найден: {cookies_file}")
            self._update_cookies_status_label()
            return

        try:
            cookies_file.unlink()
        except OSError as error:
            self._status_label.setText(f"Не удалось удалить cookies.txt: {error}")
            self._update_cookies_status_label()
            return

        self._status_label.setText(f"cookies.txt удалён безвозвратно: {cookies_file}")
        self._update_cookies_status_label()

    def _handle_start_queue_clicked(self) -> None:
        if self._active_download_future is not None:
            self._status_label.setText("Сейчас уже выполняется загрузка")
            return

        downloadable_tasks = self._container.download_queue_service.list_downloadable_tasks()

        if not downloadable_tasks:
            self._status_label.setText("В очереди нет задач для загрузки")
            return

        self._queued_download_task_ids = [task.task_id for task in downloadable_tasks]
        self._start_next_queued_download()

    def _handle_remove_selected_task_clicked(self) -> None:
        selected_task = self._get_selected_task()

        if selected_task is None:
            self._status_label.setText("Выберите задачу в очереди")
            return

        self._remove_task_from_queue(task_id=selected_task.task_id)

    def _show_queue_context_menu(self, position: QPoint) -> None:
        table_item = self._queue_table.itemAt(position)

        if table_item is None:
            return

        row_index = table_item.row()
        task_id = self._task_ids_by_row.get(row_index)

        if task_id is None:
            return

        self._queue_table.selectRow(row_index)

        context_menu = QMenu(self)
        download_action = context_menu.addAction("Скачать этот файл")
        remove_action = context_menu.addAction("Удалить из очереди")

        viewport = cast(QWidget, self._queue_table.viewport())
        selected_action = context_menu.exec(viewport.mapToGlobal(position))

        if selected_action == download_action:
            self._start_single_task_download(task_id=task_id)
            return

        if selected_action == remove_action:
            self._remove_task_from_queue(task_id=task_id)

    def _start_single_task_download(self, task_id: UUID) -> None:
        if self._active_download_future is not None:
            self._status_label.setText("Сейчас уже выполняется загрузка")
            return

        task = self._container.download_queue_service.get_task(task_id=task_id)

        if task is None:
            self._status_label.setText("Задача не найдена")
            return

        if not is_downloadable(task):
            self._status_label.setText("Эту задачу сейчас нельзя скачать повторно")
            return

        self._queued_download_task_ids = [task_id]
        self._start_next_queued_download()

    def _start_next_queued_download(self) -> None:
        if self._active_download_future is not None:
            return

        while self._queued_download_task_ids:
            task_id = self._queued_download_task_ids.pop(0)
            task = self._container.download_queue_service.get_task(task_id=task_id)

            if task is None or not is_downloadable(task):
                continue

            running_task = self._container.download_queue_service.update_status(
                task_id=task.task_id,
                status=DownloadStatus.RUNNING,
            )

            if running_task is None:
                continue

            self._update_task_row(task=running_task)
            self._active_download_task_id = running_task.task_id
            self._active_download_future = self._download_executor.submit(
                self._container.downloader.download,
                running_task,
            )
            self._set_download_controls_enabled(is_enabled=False)
            self._download_poll_timer.start(DOWNLOAD_POLL_INTERVAL_MS)
            self._status_label.setText(f"Загрузка запущена: {running_task.url.value}")
            return

        self._set_download_controls_enabled(is_enabled=True)
        self._status_label.setText("Очередь загрузок завершена")

    def _poll_download_result(self) -> None:
        if self._active_download_future is None:
            self._download_poll_timer.stop()
            return

        if not self._active_download_future.done():
            return

        future = self._active_download_future
        self._active_download_future = None
        self._active_download_task_id = None
        self._download_poll_timer.stop()

        try:
            result = future.result()
        except Exception as error:
            self._set_download_controls_enabled(is_enabled=True)
            self._status_label.setText(f"Ошибка загрузки: {error}")
            return

        updated_task = self._container.download_queue_service.apply_result(result=result)

        if updated_task is not None:
            self._update_task_row(task=updated_task)

        if self._queued_download_task_ids:
            self._start_next_queued_download()
            return

        self._set_download_controls_enabled(is_enabled=True)

        if result.status is DownloadStatus.COMPLETED:
            self._status_label.setText("Очередь загрузок завершена")
            return

        self._status_label.setText(f"Загрузка завершилась ошибкой: {result.error_message}")

    def _remove_task_from_queue(self, task_id: UUID) -> None:
        if self._active_download_task_id == task_id:
            self._status_label.setText("Нельзя удалить задачу, которая сейчас выполняется")
            return

        removed_task = self._container.download_queue_service.remove_task(task_id=task_id)

        if removed_task is None:
            self._status_label.setText("Задача не найдена")
            return

        self._queued_download_task_ids = [
            queued_task_id
            for queued_task_id in self._queued_download_task_ids
            if queued_task_id != task_id
        ]
        self._reload_queue_table()
        self._status_label.setText(f"Удалено из очереди: {removed_task.url.value}")

    def _get_selected_task(self) -> DownloadTask | None:
        row_index = self._queue_table.currentRow()

        if row_index < 0:
            return None

        task_id = self._task_ids_by_row.get(row_index)

        if task_id is None:
            return None

        return self._container.download_queue_service.get_task(task_id=task_id)

    def _get_selected_video_quality(self) -> VideoQuality:
        return cast(VideoQuality, self._quality_combo_box.currentData())

    def _get_selected_output_format(self) -> OutputFormat:
        return cast(OutputFormat, self._format_combo_box.currentData())

    def _append_task_to_table(self, task: DownloadTask) -> None:
        row_index = self._queue_table.rowCount()
        self._queue_table.insertRow(row_index)
        self._task_ids_by_row[row_index] = task.task_id
        self._row_by_task_id[task.task_id] = row_index

        self._set_task_row_values(row_index=row_index, task=task)
        self._queue_table.resizeRowsToContents()
        self._resize_queue_columns()

    def _update_task_row(self, task: DownloadTask) -> None:
        row_index = self._row_by_task_id.get(task.task_id)

        if row_index is None:
            return

        self._set_task_row_values(row_index=row_index, task=task)
        self._queue_table.resizeRowsToContents()
        self._resize_queue_columns()

    def _reload_queue_table(self) -> None:
        self._queue_table.setRowCount(0)
        self._task_ids_by_row.clear()
        self._row_by_task_id.clear()

        for task in self._container.download_queue_service.list_tasks():
            self._append_task_to_table(task=task)

        self._resize_queue_columns()

    def _set_task_row_values(self, *, row_index: int, task: DownloadTask) -> None:
        values = (
            task.mode.value,
            task.url.value,
            task.video_quality.value,
            task.output_format.value,
            task.status.value,
            str(task.target_dir),
        )

        for column_index, value in enumerate(values):
            table_item = self._queue_table.item(row_index, column_index)

            if table_item is None:
                table_item = QTableWidgetItem(value)
                self._queue_table.setItem(row_index, column_index, table_item)
            else:
                table_item.setText(value)

            table_item.setToolTip(value)

    def _resize_queue_columns(self) -> None:
        if self._queue_table.columnCount() == 0:
            return

        viewport = cast(QWidget, self._queue_table.viewport())
        available_width = max(
            viewport.width(),
            sum(MIN_COLUMN_WIDTHS.values()),
        )
        minimum_total_width = sum(MIN_COLUMN_WIDTHS.values())
        extra_width = max(0, available_width - minimum_total_width)
        total_weight = sum(COLUMN_STRETCH_WEIGHTS.values())

        calculated_widths: dict[int, int] = {}

        for column_index, minimum_width in MIN_COLUMN_WIDTHS.items():
            weighted_extra = int(extra_width * COLUMN_STRETCH_WEIGHTS[column_index] / total_weight)
            calculated_widths[column_index] = minimum_width + weighted_extra

        last_column_width = available_width - sum(
            width
            for column_index, width in calculated_widths.items()
            if column_index != FOLDER_COLUMN_INDEX
        )
        calculated_widths[FOLDER_COLUMN_INDEX] = max(
            MIN_COLUMN_WIDTHS[FOLDER_COLUMN_INDEX],
            last_column_width,
        )

        for column_index, column_width in calculated_widths.items():
            self._queue_table.setColumnWidth(column_index, column_width)

    def _update_downloads_dir_label(self) -> None:
        self._downloads_dir_label.setText(f"Папка загрузок: {self._settings.downloads_dir}")
        self._downloads_dir_label.setToolTip(str(self._settings.downloads_dir))

    def _update_cookies_status_label(self) -> None:
        cookies_file = self._container.paths.cookies_file

        if cookies_file.is_file():
            file_size = cookies_file.stat().st_size
            self._cookies_status_label.setText(f"cookies.txt: найден ({file_size} байт)")
        else:
            self._cookies_status_label.setText("cookies.txt: не найден")

        self._cookies_status_label.setToolTip(str(cookies_file))

    def _set_download_controls_enabled(self, *, is_enabled: bool) -> None:
        self._start_queue_button.setEnabled(is_enabled)
        self._remove_from_queue_button.setEnabled(is_enabled)
        self._add_to_queue_button.setEnabled(is_enabled)
        self._choose_downloads_dir_button.setEnabled(is_enabled)
        self._delete_cookies_button.setEnabled(is_enabled)
