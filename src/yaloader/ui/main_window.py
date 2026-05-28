from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from queue import Empty, SimpleQueue
from typing import Final, override
from uuid import UUID

from loguru import logger
from pydantic import ValidationError
from PyQt6.QtCore import QEvent, QTimer, QTimerEvent, QUrl
from PyQt6.QtGui import QCloseEvent, QDesktopServices, QShowEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.cancellation import DownloadCancellationToken
from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.application.dto.download_progress import DownloadProgress
from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.download_result import DownloadResult
from yaloader.application.services.download_queue_service import is_downloadable
from yaloader.config.app_info import APP_DISPLAY_NAME
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus
from yaloader.domain.format_rules import get_download_mode_for_output_format
from yaloader.services.app_container import AppContainer
from yaloader.ui.widgets.download_input_panel import DownloadInputPanel
from yaloader.ui.widgets.download_queue_table import DownloadQueueTable
from yaloader.ui.widgets.environment_panel import EnvironmentPanel
from yaloader.ui.widgets.settings_panel import SettingsPanel

WINDOW_INITIAL_WIDTH = 1180
WINDOW_INITIAL_HEIGHT = 920
WINDOW_MINIMUM_WIDTH = 1040
WINDOW_MINIMUM_HEIGHT = 760

DOWNLOAD_WORKERS_COUNT = 1
DOWNLOAD_POLL_INTERVAL_MS = 250

HISTORY_RECORD_STATUSES: Final[frozenset[DownloadStatus]] = frozenset(
    {
        DownloadStatus.COMPLETED,
        DownloadStatus.FAILED,
        DownloadStatus.CANCELED,
    }
)


class MainWindow(QMainWindow):
    def __init__(self, container: AppContainer) -> None:
        super().__init__()

        self._container = container
        self._settings = container.settings

        self._input_panel = DownloadInputPanel(self)
        self._settings_panel = SettingsPanel(self)
        self._environment_panel = EnvironmentPanel(self)
        self._queue_table = DownloadQueueTable(self)
        self._start_queue_button = QPushButton("Скачать очередь", self)
        self._remove_from_queue_button = QPushButton("Удалить выбранное", self)
        self._clear_queue_button = QPushButton("Очистить очередь", self)
        self._status_label = QLabel("Готов к работе", self)

        self._queued_download_task_ids: list[UUID] = []
        self._recorded_history_task_ids: set[UUID] = set()
        self._progress_events: SimpleQueue[DownloadProgress] = SimpleQueue()

        self._download_executor = ThreadPoolExecutor(
            max_workers=DOWNLOAD_WORKERS_COUNT,
            thread_name_prefix="yaloader-download",
        )
        self._active_download_future: Future[DownloadResult] | None = None
        self._active_download_task_id: UUID | None = None
        self._active_cancellation_token: DownloadCancellationToken | None = None
        self._download_poll_timer = self.startTimer(DOWNLOAD_POLL_INTERVAL_MS)

        self._configure_window()
        self._configure_widgets()
        self._connect_signals()
        self.setCentralWidget(self._build_central_widget())

        self._update_downloads_dir_label()
        self._refresh_environment_status()
        self._sync_queue_controls_state()
        self._focus_url_input_later()

    @override
    def showEvent(self, event: QShowEvent | None) -> None:
        super().showEvent(event)
        self._focus_url_input_later()

    @override
    def changeEvent(self, event: QEvent | None) -> None:
        super().changeEvent(event)

        if event is None:
            return

        if event.type() is QEvent.Type.WindowStateChange and not self.isMinimized():
            self._focus_url_input_later()

    @override
    def closeEvent(self, event: QCloseEvent | None) -> None:
        if self._active_cancellation_token is not None:
            self._active_cancellation_token.request_cancel()

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
        self._start_queue_button.setObjectName("PrimaryButton")
        self._remove_from_queue_button.setObjectName("SecondaryButton")
        self._clear_queue_button.setObjectName("SecondaryButton")
        self._queue_table.set_context_menu_callbacks(
            on_download_tasks=self._start_tasks_download,
            on_cancel_task=self._cancel_task_download,
            on_remove_tasks=self._remove_tasks_from_queue,
        )
        self._sync_start_queue_button_state()

    def _connect_signals(self) -> None:
        self._input_panel.add_to_queue_button.clicked.connect(self._handle_add_to_queue_clicked)
        self._start_queue_button.clicked.connect(self._handle_start_or_cancel_queue_clicked)
        self._remove_from_queue_button.clicked.connect(self._handle_remove_selected_tasks_clicked)
        self._clear_queue_button.clicked.connect(self._handle_clear_queue_clicked)
        self._queue_table.itemSelectionChanged.connect(self._sync_queue_controls_state)
        self._settings_panel.choose_downloads_dir_button.clicked.connect(
            self._handle_choose_downloads_dir_clicked
        )
        self._environment_panel.delete_cookies_button.clicked.connect(
            self._handle_delete_cookies_clicked
        )
        self._environment_panel.refresh_button.clicked.connect(
            self._handle_refresh_environment_status_clicked
        )
        self._environment_panel.open_cookies_dir_button.clicked.connect(self._open_cookies_dir)
        self._environment_panel.open_downloads_dir_button.clicked.connect(self._open_downloads_dir)

    def _build_central_widget(self) -> QWidget:
        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(28, 24, 28, 24)
        root_layout.setSpacing(18)

        root_layout.addWidget(self._build_header())
        root_layout.addWidget(self._input_panel)
        root_layout.addWidget(self._build_queue_panel(), stretch=1)
        root_layout.addWidget(self._settings_panel)
        root_layout.addWidget(self._environment_panel)
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
            self._focus_url_input_later()
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
            self._focus_url_input_later()
            return

        existing_task = self._container.download_queue_service.get_task_by_url(url=request.url)

        if existing_task is not None:
            self._status_label.setText("Эта ссылка уже есть в очереди")
            self._focus_url_input_later()
            return

        task = self._container.download_queue_service.add_download(request=request)
        self._queue_table.append_task(task=task)

        self._input_panel.clear_url()
        self._status_label.setText(
            f"Добавлено в очередь: {self._container.download_queue_service.count()}"
        )
        self._sync_queue_controls_state()
        self._focus_url_input_later()

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
        self._refresh_environment_status()
        self._status_label.setText(f"Папка загрузок изменена: {downloads_dir}")

    def _handle_delete_cookies_clicked(self) -> None:
        cookies_file = self._container.paths.cookies_file

        if not cookies_file.is_file():
            self._status_label.setText(f"cookies.txt не найден: {cookies_file}")
            self._refresh_environment_status()
            return

        try:
            cookies_file.unlink()
        except OSError as error:
            self._status_label.setText(f"Не удалось удалить cookies.txt: {error}")
            self._refresh_environment_status()
            return

        self._status_label.setText(f"cookies.txt удалён безвозвратно: {cookies_file}")
        self._refresh_environment_status()

    def _handle_start_or_cancel_queue_clicked(self) -> None:
        if self._active_download_future is not None:
            self._cancel_active_download()
            return

        self._handle_start_queue_clicked()

    def _handle_start_queue_clicked(self) -> None:
        if self._active_download_future is not None:
            self._status_label.setText("Сейчас уже выполняется загрузка")
            return

        downloadable_tasks = self._container.download_queue_service.list_downloadable_tasks()

        if not downloadable_tasks:
            self._status_label.setText("В очереди нет задач для загрузки")
            self._sync_queue_controls_state()
            return

        queued_task_ids = tuple(task.task_id for task in downloadable_tasks)
        self._queued_download_task_ids = list(queued_task_ids)
        self._queue_table.prepare_tasks_for_download(task_ids=queued_task_ids)
        self._start_next_queued_download()

    def _handle_remove_selected_tasks_clicked(self) -> None:
        selected_task_ids = self._queue_table.get_selected_task_ids()

        if not selected_task_ids:
            self._status_label.setText("Выберите задачи в очереди")
            self._sync_queue_controls_state()
            return

        self._remove_tasks_from_queue(task_ids=selected_task_ids)

    def _handle_clear_queue_clicked(self) -> None:
        if self._active_download_future is not None:
            self._status_label.setText("Нельзя очистить очередь во время загрузки")
            return

        removed_count = self._container.download_queue_service.clear_tasks()
        self._queued_download_task_ids.clear()
        self._queue_table.reload_tasks(())

        if removed_count == 0:
            self._status_label.setText("Очередь уже пустая")
            self._sync_queue_controls_state()
            return

        self._status_label.setText(f"Очередь очищена. Удалено задач: {removed_count}")
        self._sync_queue_controls_state()

    def _start_tasks_download(self, task_ids: tuple[UUID, ...]) -> None:
        if self._active_download_future is not None:
            self._status_label.setText("Сейчас уже выполняется загрузка")
            return

        downloadable_task_ids: list[UUID] = []

        for task_id in task_ids:
            task = self._container.download_queue_service.get_task(task_id=task_id)

            if task is not None and is_downloadable(task):
                downloadable_task_ids.append(task.task_id)

        if not downloadable_task_ids:
            self._status_label.setText("Среди выбранных задач нет доступных для загрузки")
            self._sync_queue_controls_state()
            return

        queued_task_ids = tuple(downloadable_task_ids)
        self._queued_download_task_ids = list(queued_task_ids)
        self._queue_table.prepare_tasks_for_download(task_ids=queued_task_ids)
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
            self._active_cancellation_token = DownloadCancellationToken()
            self._active_download_future = self._download_executor.submit(
                self._container.downloader.download,
                task=running_task,
                progress_callback=self._handle_download_progress,
                cancellation_token=self._active_cancellation_token,
            )
            self._set_download_controls_enabled(is_enabled=False)
            self._status_label.setText(f"Загрузка запущена: {running_task.url.value}")
            return

        self._set_download_controls_enabled(is_enabled=True)
        self._status_label.setText("Очередь загрузок завершена")

    def _cancel_active_download(self) -> None:
        if self._active_cancellation_token is None or self._active_download_task_id is None:
            self._status_label.setText("Нет активной загрузки для отмены")
            return

        task_ids_to_cancel = self._build_prepared_task_ids_for_cancel()
        self._queued_download_task_ids.clear()
        self._active_cancellation_token.request_cancel()

        for task_id in task_ids_to_cancel:
            canceled_task = self._container.download_queue_service.update_status(
                task_id=task_id,
                status=DownloadStatus.CANCELED,
                error_message="Загрузка отменена пользователем.",
            )

            if canceled_task is not None:
                self._queue_table.update_task(task=canceled_task)
                self._record_download_history(task=canceled_task, output_path=None)

        self._status_label.setText("Отмена загрузки... Частичные файлы будут удалены")
        self._sync_queue_controls_state()

    def _build_prepared_task_ids_for_cancel(self) -> tuple[UUID, ...]:
        task_ids: list[UUID] = []
        seen_task_ids: set[UUID] = set()

        if self._active_download_task_id is not None:
            task_ids.append(self._active_download_task_id)
            seen_task_ids.add(self._active_download_task_id)

        for task_id in self._queued_download_task_ids:
            if task_id in seen_task_ids:
                continue

            task_ids.append(task_id)
            seen_task_ids.add(task_id)

        return tuple(task_ids)

    def _cancel_task_download(self, task_id: UUID) -> None:
        if self._active_download_task_id != task_id:
            self._status_label.setText("Отменить можно только активную загрузку")
            return

        self._cancel_active_download()

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
        self._active_cancellation_token = None

        try:
            result = future.result()
        except Exception as error:
            self._set_download_controls_enabled(is_enabled=True)
            self._status_label.setText(f"Ошибка загрузки: {error}")
            return

        self._drain_progress_events()
        updated_task = self._apply_download_result(result=result)

        if updated_task is not None:
            self._queue_table.update_task(task=updated_task)
            self._record_download_history(task=updated_task, output_path=result.output_path)

        if self._queued_download_task_ids:
            self._start_next_queued_download()
            return

        self._set_download_controls_enabled(is_enabled=True)

        if updated_task is not None and updated_task.status is DownloadStatus.CANCELED:
            self._status_label.setText("Загрузка отменена. Частичные файлы удалены")
            return

        if result.status is DownloadStatus.COMPLETED:
            self._status_label.setText("Очередь загрузок завершена")
            return

        self._status_label.setText(f"Загрузка завершилась ошибкой: {result.error_message}")

    def _apply_download_result(self, *, result: DownloadResult) -> DownloadTask | None:
        current_task = self._container.download_queue_service.get_task(task_id=result.task_id)

        if current_task is not None and current_task.status is DownloadStatus.CANCELED:
            return current_task

        return self._container.download_queue_service.apply_result(result=result)

    def _record_download_history(
        self,
        *,
        task: DownloadTask,
        output_path: Path | None,
    ) -> None:
        if task.task_id in self._recorded_history_task_ids:
            return

        if task.status not in HISTORY_RECORD_STATUSES:
            return

        record = DownloadHistoryRecord.create_from_task(
            task=task,
            output_path=output_path,
        )

        try:
            self._container.download_history_service.append(record=record)
        except OSError as error:
            logger.warning(
                "Failed to save download history. task_id={} error={}",
                task.task_id,
                error,
            )
            return

        self._recorded_history_task_ids.add(task.task_id)

    def _drain_progress_events(self) -> None:
        while True:
            try:
                progress = self._progress_events.get_nowait()
            except Empty:
                return

            task = self._container.download_queue_service.get_task(task_id=progress.task_id)

            if task is not None and task.status is DownloadStatus.CANCELED:
                continue

            self._queue_table.set_task_progress(progress=progress)

    def _remove_tasks_from_queue(self, task_ids: tuple[UUID, ...]) -> None:
        if self._active_download_task_id in task_ids:
            self._status_label.setText("Нельзя удалить задачу, которая сейчас выполняется")
            return

        removed_count = 0

        for task_id in task_ids:
            removed_task = self._container.download_queue_service.remove_task(task_id=task_id)

            if removed_task is not None:
                removed_count += 1

        self._queued_download_task_ids = [
            queued_task_id
            for queued_task_id in self._queued_download_task_ids
            if queued_task_id not in task_ids
        ]
        self._queue_table.reload_tasks(self._container.download_queue_service.list_tasks())

        if removed_count == 0:
            self._status_label.setText("Выбранные задачи не найдены")
            self._sync_queue_controls_state()
            return

        self._status_label.setText(f"Удалено из очереди: {removed_count}")
        self._sync_queue_controls_state()

    def _refresh_environment_status(self) -> None:
        status = self._container.environment_check_service.check(
            downloads_dir=self._settings.downloads_dir,
        )
        self._environment_panel.set_status(status=status)

    def _handle_refresh_environment_status_clicked(self) -> None:
        self._refresh_environment_status()
        self._environment_panel.play_refresh_feedback()

    def _open_cookies_dir(self) -> None:
        self._container.paths.data_dir.mkdir(parents=True, exist_ok=True)
        self._open_directory(self._container.paths.data_dir)

    def _open_downloads_dir(self) -> None:
        self._settings.downloads_dir.mkdir(parents=True, exist_ok=True)
        self._open_directory(self._settings.downloads_dir)

    def _open_directory(self, directory: Path) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    def _update_downloads_dir_label(self) -> None:
        self._settings_panel.set_downloads_dir(downloads_dir=self._settings.downloads_dir)

    def _set_download_controls_enabled(self, *, is_enabled: bool) -> None:
        self._input_panel.add_to_queue_button.setEnabled(is_enabled)
        self._settings_panel.choose_downloads_dir_button.setEnabled(is_enabled)
        self._environment_panel.delete_cookies_button.setEnabled(is_enabled)
        self._environment_panel.refresh_button.setEnabled(is_enabled)
        self._environment_panel.open_cookies_dir_button.setEnabled(is_enabled)
        self._environment_panel.open_downloads_dir_button.setEnabled(is_enabled)
        self._sync_queue_controls_state()

    def _sync_queue_controls_state(self) -> None:
        has_tasks = self._queue_table.has_tasks()
        has_selected_tasks = bool(self._queue_table.get_selected_task_ids())
        has_downloadable_tasks = bool(
            self._container.download_queue_service.list_downloadable_tasks()
        )
        has_active_download = self._active_download_future is not None

        self._start_queue_button.setEnabled(has_active_download or has_downloadable_tasks)
        self._remove_from_queue_button.setEnabled(has_selected_tasks and not has_active_download)
        self._clear_queue_button.setEnabled(has_tasks and not has_active_download)
        self._sync_start_queue_button_state()

    def _sync_start_queue_button_state(self) -> None:
        if self._active_download_future is not None:
            self._start_queue_button.setText("Отменить загрузку")
            self._start_queue_button.setObjectName("DangerButton")
        else:
            self._start_queue_button.setText("Скачать очередь")
            self._start_queue_button.setObjectName("PrimaryButton")

        style = self._start_queue_button.style()

        if isinstance(style, QStyle):
            style.unpolish(self._start_queue_button)
            style.polish(self._start_queue_button)

    def _focus_url_input_later(self) -> None:
        QTimer.singleShot(0, self._input_panel.focus_url_input)
