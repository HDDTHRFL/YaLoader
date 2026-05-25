from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from queue import Empty, SimpleQueue
from typing import override
from uuid import UUID

from pydantic import ValidationError
from PyQt6.QtCore import QTimerEvent
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.services.download_queue_service import is_downloadable
from yaloader.config.app_info import APP_DISPLAY_NAME
from yaloader.domain.enums import DownloadStatus
from yaloader.domain.format_rules import get_download_mode_for_output_format
from yaloader.services.app_container import AppContainer
from yaloader.ui.widgets.download_input_panel import DownloadInputPanel
from yaloader.ui.widgets.download_queue_table import DownloadQueueTable
from yaloader.ui.widgets.settings_panel import SettingsPanel

WINDOW_INITIAL_WIDTH = 1180
WINDOW_INITIAL_HEIGHT = 850
WINDOW_MINIMUM_WIDTH = 1040
WINDOW_MINIMUM_HEIGHT = 680

DOWNLOAD_WORKERS_COUNT = 1
DOWNLOAD_POLL_INTERVAL_MS = 250


class MainWindow(QMainWindow):
    def __init__(self, container: AppContainer) -> None:
        super().__init__()

        self._container = container
        self._settings = container.settings

        self._input_panel = DownloadInputPanel(self)
        self._settings_panel = SettingsPanel(self)
        self._queue_table = DownloadQueueTable(self)
        self._start_queue_button = QPushButton("Скачать очередь", self)
        self._remove_from_queue_button = QPushButton("Удалить выбранное", self)
        self._clear_queue_button = QPushButton("Очистить очередь", self)
        self._status_label = QLabel("Готов к работе", self)

        self._queued_download_task_ids: list[UUID] = []
        self._progress_events: SimpleQueue[DownloadProgress] = SimpleQueue()

        self._download_executor = ThreadPoolExecutor(
            max_workers=DOWNLOAD_WORKERS_COUNT,
            thread_name_prefix="yaloader-download",
        )
        self._active_download_future: Future[DownloadResult] | None = None
        self._active_download_task_id: UUID | None = None
        self._download_poll_timer = self.startTimer(DOWNLOAD_POLL_INTERVAL_MS)

        self._configure_window()
        self._configure_widgets()
        self._connect_signals()
        self.setCentralWidget(self._build_central_widget())

        self._update_downloads_dir_label()
        self._update_cookies_status_label()

    @override
    def closeEvent(self, event: QCloseEvent | None) -> None:
        self.killTimer(self._download_poll_timer)
        self._download_executor.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)

    @override
    def timerEvent(self, event: QTimerEvent | None) -> None:
        if event is not None and event.timerId() != self._download_poll_timer:
            super().timerEvent(event)
            return

        self._poll_download_result()

    def _configure_window(self) -> None:
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(WINDOW_INITIAL_WIDTH, WINDOW_INITIAL_HEIGHT)
        self.setMinimumSize(WINDOW_MINIMUM_WIDTH, WINDOW_MINIMUM_HEIGHT)

    def _configure_widgets(self) -> None:
        self._status_label.setObjectName("StatusLabel")
        self._queue_table.set_context_menu_callbacks(
            on_download_task=self._start_single_task_download,
            on_remove_task=self._remove_task_from_queue,
        )

    def _connect_signals(self) -> None:
        self._input_panel.add_to_queue_button.clicked.connect(self._handle_add_to_queue_clicked)
        self._start_queue_button.clicked.connect(self._handle_start_queue_clicked)
        self._remove_from_queue_button.clicked.connect(self._handle_remove_selected_task_clicked)
        self._clear_queue_button.clicked.connect(self._handle_clear_queue_clicked)
        self._settings_panel.choose_downloads_dir_button.clicked.connect(
            self._handle_choose_downloads_dir_clicked
        )
        self._settings_panel.delete_cookies_button.clicked.connect(
            self._handle_delete_cookies_clicked
        )

    def _build_central_widget(self) -> QWidget:
        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(28, 24, 28, 24)
        root_layout.setSpacing(18)

        root_layout.addWidget(self._build_header())
        root_layout.addWidget(self._input_panel)
        root_layout.addWidget(self._settings_panel)
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
        actions_layout.addWidget(self._clear_queue_button)
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
        url = self._input_panel.get_url_text()

        if not url:
            self._status_label.setText("Сначала вставьте ссылку")
            return

        selected_output_format = self._input_panel.get_selected_output_format()
        selected_video_quality = self._input_panel.get_selected_video_quality()

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
        self._queue_table.append_task(task=task)

        self._input_panel.clear_url()
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
        selected_task_id = self._queue_table.get_selected_task_id()

        if selected_task_id is None:
            self._status_label.setText("Выберите задачу в очереди")
            return

        self._remove_task_from_queue(task_id=selected_task_id)

    def _handle_clear_queue_clicked(self) -> None:
        if self._active_download_future is not None:
            self._status_label.setText("Нельзя очистить очередь во время загрузки")
            return

        removed_count = self._container.download_queue_service.clear_tasks()
        self._queued_download_task_ids.clear()
        self._queue_table.reload_tasks(())

        if removed_count == 0:
            self._status_label.setText("Очередь уже пустая")
            return

        self._status_label.setText(f"Очередь очищена. Удалено задач: {removed_count}")

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

            self._queue_table.update_task(task=running_task)
            self._queue_table.set_task_progress(
                DownloadProgress.started(task_id=running_task.task_id)
            )
            self._active_download_task_id = running_task.task_id
            self._active_download_future = self._download_executor.submit(
                self._container.downloader.download,
                running_task,
                self._handle_download_progress,
            )
            self._set_download_controls_enabled(is_enabled=False)
            self._status_label.setText(f"Загрузка запущена: {running_task.url.value}")
            return

        self._set_download_controls_enabled(is_enabled=True)
        self._status_label.setText("Очередь загрузок завершена")

    def _handle_download_progress(self, progress: DownloadProgress) -> None:
        self._progress_events.put(progress)

    def _poll_download_result(self) -> None:
        self._drain_progress_events()

        if self._active_download_future is None:
            return

        if not self._active_download_future.done():
            return

        future = self._active_download_future
        self._active_download_future = None
        self._active_download_task_id = None

        try:
            result = future.result()
        except Exception as error:
            self._set_download_controls_enabled(is_enabled=True)
            self._status_label.setText(f"Ошибка загрузки: {error}")
            return

        self._drain_progress_events()
        updated_task = self._container.download_queue_service.apply_result(result=result)

        if updated_task is not None:
            self._queue_table.update_task(task=updated_task)

        if self._queued_download_task_ids:
            self._start_next_queued_download()
            return

        self._set_download_controls_enabled(is_enabled=True)

        if result.status is DownloadStatus.COMPLETED:
            self._status_label.setText("Очередь загрузок завершена")
            return

        self._status_label.setText(f"Загрузка завершилась ошибкой: {result.error_message}")

    def _drain_progress_events(self) -> None:
        while True:
            try:
                progress = self._progress_events.get_nowait()
            except Empty:
                return

            self._queue_table.set_task_progress(progress=progress)

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
        self._queue_table.reload_tasks(self._container.download_queue_service.list_tasks())
        self._status_label.setText(f"Удалено из очереди: {removed_task.url.value}")

    def _update_downloads_dir_label(self) -> None:
        self._settings_panel.set_downloads_dir(downloads_dir=self._settings.downloads_dir)

    def _update_cookies_status_label(self) -> None:
        self._settings_panel.set_cookies_status(cookies_file=self._container.paths.cookies_file)

    def _set_download_controls_enabled(self, *, is_enabled: bool) -> None:
        self._start_queue_button.setEnabled(is_enabled)
        self._remove_from_queue_button.setEnabled(is_enabled)
        self._clear_queue_button.setEnabled(is_enabled)
        self._input_panel.add_to_queue_button.setEnabled(is_enabled)
        self._settings_panel.choose_downloads_dir_button.setEnabled(is_enabled)
        self._settings_panel.delete_cookies_button.setEnabled(is_enabled)
