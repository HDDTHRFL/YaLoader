from __future__ import annotations

from pathlib import Path
from typing import override
from uuid import UUID

from PyQt6.QtCore import QEvent, QTimer, QTimerEvent, QUrl
from PyQt6.QtGui import QCloseEvent, QDesktopServices, QShowEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.application.dto.download_request import DownloadRequest
from yaloader.config.app_info import APP_DISPLAY_NAME
from yaloader.domain.enums import DownloadStatus, VideoQuality
from yaloader.services.app_container import AppContainer
from yaloader.ui.controllers.download_controller import (
    DownloadController,
    DownloadControllerUpdate,
)
from yaloader.ui.controllers.environment_controller import (
    EnvironmentController,
    EnvironmentControllerUpdate,
)
from yaloader.ui.controllers.history_controller import (
    HistoryController,
    HistoryControllerUpdate,
)
from yaloader.ui.controllers.media_metadata_controller import (
    MediaMetadataController,
    MediaMetadataResolutionResult,
)
from yaloader.ui.controllers.queue_input_controller import (
    QueueInputController,
    QueueInputControllerUpdate,
)
from yaloader.ui.footer_status_presenter import FooterStatusPresenter
from yaloader.ui.status_messages import (
    DEFAULT_STATUS_MESSAGE,
    is_primary_download_status_message,
)
from yaloader.ui.widgets.app_header import AppHeader
from yaloader.ui.widgets.common.confirmation_dialogs import confirm_dangerous_action
from yaloader.ui.widgets.download_input_panel import DownloadInputPanel
from yaloader.ui.widgets.download_queue.panel import DownloadQueuePanel
from yaloader.ui.widgets.environment_panel import EnvironmentPanel
from yaloader.ui.widgets.history.panel import HISTORY_PANEL_WIDTH, HistoryPanel
from yaloader.ui.widgets.settings_panel import SettingsPanel

WINDOW_INITIAL_WIDTH = 1180
WINDOW_INITIAL_HEIGHT = 920
WINDOW_MINIMUM_WIDTH = 1040
WINDOW_MINIMUM_HEIGHT = 760

DOWNLOAD_POLL_INTERVAL_MS = 250

CLEAR_QUEUE_CONFIRMATION_TITLE = "Очистить очередь?"
CLEAR_QUEUE_CONFIRMATION_TEXT = "Очередь загрузок будет полностью очищена."
CLEAR_QUEUE_CONFIRMATION_DETAILS = (
    "Все задачи из списка будут удалены. Уже скачанные файлы на диске не удаляются."
)
CLEAR_QUEUE_CONFIRMATION_BUTTON = "Очистить очередь"

DELETE_COOKIES_CONFIRMATION_TITLE = "Удалить cookies.txt?"
DELETE_COOKIES_CONFIRMATION_TEXT = "Файл cookies.txt будет удалён безвозвратно."
DELETE_COOKIES_CONFIRMATION_DETAILS = "При необходимости cookies.txt придётся создать заново."
DELETE_COOKIES_CONFIRMATION_BUTTON = "Удалить cookies.txt"

CLEAR_HISTORY_CONFIRMATION_TITLE = "Очистить историю?"
CLEAR_HISTORY_CONFIRMATION_TEXT = "История загрузок будет полностью очищена."
CLEAR_HISTORY_CONFIRMATION_DETAILS = (
    "Записи истории будут удалены из YaLoader. Скачанные файлы на диске не удаляются."
)
CLEAR_HISTORY_CONFIRMATION_BUTTON = "Очистить историю"


class MainWindow(QMainWindow):
    def __init__(self, container: AppContainer) -> None:
        super().__init__()

        self._container = container
        self._settings = container.settings

        self._header = AppHeader(self)
        self._input_panel = DownloadInputPanel(self)
        self._settings_panel = SettingsPanel(self)
        self._environment_panel = EnvironmentPanel(self)
        self._queue_panel = DownloadQueuePanel(self)
        self._history_panel = HistoryPanel(self)

        self._queue_table = self._queue_panel.queue_table
        self._start_queue_button = self._queue_panel.start_queue_button
        self._remove_from_queue_button = self._queue_panel.remove_from_queue_button
        self._clear_queue_button = self._queue_panel.clear_queue_button
        self._history_toggle_button = self._header.history_toggle_button

        self._status_label = QLabel(DEFAULT_STATUS_MESSAGE, self)
        self._footer_status_presenter = FooterStatusPresenter(
            label=self._status_label,
            parent=self,
        )

        self._metadata_controller = MediaMetadataController(
            service=container.media_metadata_service,
        )
        self._download_controller = DownloadController(
            queue_service=container.download_queue_service,
            history_service=container.download_history_service,
            downloader=container.downloader,
        )
        self._history_controller = HistoryController(
            history_service=container.download_history_service,
            queue_service=container.download_queue_service,
        )
        self._queue_input_controller = QueueInputController(
            queue_service=container.download_queue_service,
        )
        self._environment_controller = EnvironmentController(
            paths=container.paths,
            settings_service=container.settings_service,
            environment_check_service=container.environment_check_service,
        )

        self._is_history_panel_visible = False
        self._download_poll_timer = self.startTimer(DOWNLOAD_POLL_INTERVAL_MS)

        self._configure_window()
        self._configure_widgets()
        self._connect_signals()
        self.setCentralWidget(self._build_central_widget())

        self._update_downloads_dir_label()
        self._apply_environment_update(
            update=self._environment_controller.load_status(
                downloads_dir=self._settings.downloads_dir,
            )
        )
        self._reload_history_panel()
        self._sync_queue_controls_state()
        self._sync_history_panel_visibility()
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
        self._footer_status_presenter.shutdown()
        self.killTimer(self._download_poll_timer)
        self._download_controller.shutdown()
        self._metadata_controller.shutdown()
        super().closeEvent(event)

    @override
    def timerEvent(self, event: QTimerEvent | None) -> None:
        if event is not None and event.timerId() != self._download_poll_timer:
            super().timerEvent(event)
            return

        self._drain_metadata_events()
        self._apply_download_update(update=self._download_controller.poll())

    def _configure_window(self) -> None:
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(WINDOW_INITIAL_WIDTH, WINDOW_INITIAL_HEIGHT)
        self.setMinimumSize(WINDOW_MINIMUM_WIDTH, WINDOW_MINIMUM_HEIGHT)

    def _configure_widgets(self) -> None:
        self._status_label.setObjectName("StatusLabel")

        self._queue_table.set_context_menu_callbacks(
            on_download_tasks=self._start_tasks_download,
            on_cancel_task=self._cancel_task_download,
            on_remove_tasks=self._remove_tasks_from_queue,
        )
        self._history_panel.set_context_menu_callbacks(
            on_add_to_queue=self._handle_add_history_record_to_queue,
            on_delete_record=self._handle_delete_history_record,
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
        self._environment_panel.open_cookies_dir_button.clicked.connect(
            self._handle_open_cookies_dir_clicked
        )
        self._environment_panel.open_downloads_dir_button.clicked.connect(
            self._handle_open_downloads_dir_clicked
        )

        self._history_toggle_button.clicked.connect(self._toggle_history_panel)
        self._history_panel.refresh_button.clicked.connect(self._handle_refresh_history_clicked)
        self._history_panel.clear_button.clicked.connect(self._handle_clear_history_clicked)

    def _build_central_widget(self) -> QWidget:
        central_widget = QWidget(self)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_main_content_widget(), stretch=1)
        root_layout.addWidget(self._history_panel)

        return central_widget

    def _build_main_content_widget(self) -> QWidget:
        main_content_widget = QWidget(self)
        root_layout = QVBoxLayout(main_content_widget)
        root_layout.setContentsMargins(28, 10, 28, 24)
        root_layout.setSpacing(18)

        root_layout.addWidget(self._header)
        root_layout.addWidget(self._input_panel)
        root_layout.addWidget(self._queue_panel, stretch=1)
        root_layout.addWidget(self._settings_panel)
        root_layout.addWidget(self._environment_panel)
        root_layout.addWidget(self._build_footer())

        return main_content_widget

    def _build_footer(self) -> QWidget:
        footer = QWidget(self)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._status_label)
        layout.addStretch(1)

        return footer

    def _toggle_history_panel(self) -> None:
        if self._is_history_panel_visible:
            self._is_history_panel_visible = False
            self._sync_history_panel_visibility()
            self.resize(
                max(self.minimumWidth(), self.width() - HISTORY_PANEL_WIDTH),
                self.height(),
            )
            return

        self._is_history_panel_visible = True
        self._sync_history_panel_visibility()
        self.resize(self.width() + HISTORY_PANEL_WIDTH, self.height())

    def _sync_history_panel_visibility(self) -> None:
        self._history_panel.setVisible(self._is_history_panel_visible)
        self._header.set_history_visible(is_visible=self._is_history_panel_visible)

    def _reload_history_panel(self) -> None:
        self._apply_history_update(update=self._history_controller.load())

    def _handle_refresh_history_clicked(self) -> None:
        self._apply_history_update(update=self._history_controller.load())
        self._show_transient_status_message("История обновлена")

    def _handle_clear_history_clicked(self) -> None:
        if self._history_panel.has_records() and not self._confirm_clear_history():
            return

        self._apply_history_update(update=self._history_controller.clear())

    def _handle_add_history_record_to_queue(self, record: DownloadHistoryRecord) -> None:
        if self._download_controller.is_active:
            self._show_transient_status_message(
                "Нельзя добавить задачу из истории во время загрузки"
            )
            return

        self._apply_history_update(
            update=self._history_controller.add_record_to_queue(record=record)
        )

    def _handle_delete_history_record(self, record: DownloadHistoryRecord) -> None:
        self._apply_history_update(update=self._history_controller.remove_record(record=record))

    def _apply_history_update(self, *, update: HistoryControllerUpdate) -> None:
        if update.records is not None:
            self._history_panel.set_records(records=update.records)

        if update.should_clear_download_history_flags:
            self._download_controller.clear_recorded_history_flags()

        if update.added_task is not None:
            self._queue_table.append_task(task=update.added_task)

        if update.added_task is not None and update.metadata_request is not None:
            self._start_metadata_resolution(
                task_id=update.added_task.task_id,
                request=update.metadata_request,
            )

        if update.status_message is not None:
            self._show_transient_status_message(update.status_message)

        self._sync_queue_controls_state()

    def _start_metadata_resolution(
        self,
        *,
        task_id: UUID,
        request: DownloadRequest,
    ) -> None:
        is_started = self._metadata_controller.start_resolution(
            task_id=task_id,
            request=request,
        )

        if is_started:
            self._queue_table.mark_quality_resolution_pending(task_id=task_id)

    def _drain_metadata_events(self) -> None:
        for result in self._metadata_controller.drain_results():
            self._apply_metadata_result(result=result)

    def _apply_metadata_result(self, *, result: MediaMetadataResolutionResult) -> None:
        self._queue_table.clear_quality_resolution_pending(task_id=result.task_id)

        if result.metadata is None:
            self._queue_table.mark_metadata_resolution_failed(task_id=result.task_id)
            self._show_transient_status_message(
                "Не удалось определить качество. yt-dlp выберет доступный вариант при скачивании"
            )
            return

        updated_task = self._container.download_queue_service.apply_metadata(
            task_id=result.task_id,
            title=result.metadata.title,
            video_quality=result.metadata.resolved_video_quality,
        )

        if updated_task is None:
            return

        if updated_task.status is DownloadStatus.RUNNING:
            return

        self._queue_table.update_task(task=updated_task)

        if result.metadata.requested_video_quality is VideoQuality.BEST:
            self._show_transient_status_message(
                f"Качество определено: {result.metadata.resolved_video_quality.value}"
            )
            return

        if result.metadata.resolved_video_quality is not result.metadata.requested_video_quality:
            self._show_transient_status_message(
                "Выбранное качество недоступно. "
                f"Будет использовано: {result.metadata.resolved_video_quality.value}"
            )
            return

        self._show_transient_status_message(
            f"Качество подтверждено: {result.metadata.resolved_video_quality.value}"
        )

    def _handle_add_to_queue_clicked(self) -> None:
        self._apply_queue_input_update(
            update=self._queue_input_controller.add_from_input(
                url=self._input_panel.get_url_text(),
                target_dir=self._settings.downloads_dir,
                output_format=self._input_panel.get_selected_output_format(),
                video_quality=self._input_panel.get_selected_video_quality(),
            )
        )

    def _apply_queue_input_update(self, *, update: QueueInputControllerUpdate) -> None:
        if update.added_task is not None:
            self._queue_table.append_task(task=update.added_task)

        if update.added_task is not None and update.metadata_request is not None:
            self._start_metadata_resolution(
                task_id=update.added_task.task_id,
                request=update.metadata_request,
            )

        if update.should_clear_url_input:
            self._input_panel.clear_url()

        if update.status_message is not None:
            self._show_transient_status_message(update.status_message)

        self._sync_queue_controls_state()

        if update.should_focus_url_input:
            self._focus_url_input_later()

    def _handle_choose_downloads_dir_clicked(self) -> None:
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для загрузок",
            str(self._settings.downloads_dir),
        )

        if not selected_dir:
            return

        self._apply_environment_update(
            update=self._environment_controller.change_downloads_dir(
                downloads_dir=Path(selected_dir),
            )
        )

    def _handle_delete_cookies_clicked(self) -> None:
        if self._container.paths.cookies_file.is_file() and not self._confirm_delete_cookies():
            return

        self._apply_environment_update(
            update=self._environment_controller.delete_cookies(
                downloads_dir=self._settings.downloads_dir,
            )
        )

    def _handle_refresh_environment_status_clicked(self) -> None:
        self._apply_environment_update(
            update=self._environment_controller.refresh_status(
                downloads_dir=self._settings.downloads_dir,
            )
        )

    def _handle_open_cookies_dir_clicked(self) -> None:
        self._apply_environment_update(update=self._environment_controller.open_cookies_dir())

    def _handle_open_downloads_dir_clicked(self) -> None:
        self._apply_environment_update(
            update=self._environment_controller.open_downloads_dir(
                downloads_dir=self._settings.downloads_dir,
            )
        )

    def _apply_environment_update(self, *, update: EnvironmentControllerUpdate) -> None:
        if update.settings is not None:
            self._settings = update.settings
            self._update_downloads_dir_label()

        if update.environment_status is not None:
            self._environment_panel.set_status(status=update.environment_status)

        if update.should_play_refresh_feedback:
            self._environment_panel.play_refresh_feedback()

        if update.directory_to_open is not None:
            self._open_directory(directory=update.directory_to_open)

        if update.status_message is not None:
            self._show_transient_status_message(update.status_message)

        self._sync_queue_controls_state()

    def _handle_start_or_cancel_queue_clicked(self) -> None:
        if self._download_controller.is_active:
            self._apply_download_update(update=self._download_controller.cancel_active_download())
            return

        self._apply_download_update(update=self._download_controller.start_downloadable_queue())

    def _handle_remove_selected_tasks_clicked(self) -> None:
        selected_task_ids = self._queue_table.get_selected_task_ids()

        if not selected_task_ids:
            self._show_transient_status_message("Выберите задачи в очереди")
            self._sync_queue_controls_state()
            return

        self._remove_tasks_from_queue(task_ids=selected_task_ids)

    def _handle_clear_queue_clicked(self) -> None:
        if self._queue_table.has_tasks() and not self._confirm_clear_queue():
            return

        self._apply_download_update(update=self._download_controller.clear_queue())

    def _start_tasks_download(self, task_ids: tuple[UUID, ...]) -> None:
        self._apply_download_update(update=self._download_controller.start_tasks(task_ids=task_ids))

    def _cancel_task_download(self, task_id: UUID) -> None:
        self._apply_download_update(
            update=self._download_controller.cancel_task_download(task_id=task_id)
        )

    def _remove_tasks_from_queue(self, task_ids: tuple[UUID, ...]) -> None:
        self._apply_download_update(
            update=self._download_controller.remove_tasks_from_queue(task_ids=task_ids)
        )

    def _apply_download_update(self, *, update: DownloadControllerUpdate) -> None:
        if update.tasks_snapshot is not None:
            self._queue_table.reload_tasks(update.tasks_snapshot)

        if update.prepared_task_ids:
            self._queue_table.prepare_tasks_for_download(task_ids=update.prepared_task_ids)

        for task in update.updated_tasks:
            self._queue_table.update_task(task=task)

        for progress in update.progress_events:
            self._queue_table.set_task_progress(progress=progress)

        if update.should_reload_history:
            self._reload_history_panel()

        if update.status_message is not None:
            self._apply_download_status_message(message=update.status_message)

        self._sync_queue_controls_state()

    def _apply_download_status_message(self, *, message: str) -> None:
        if is_primary_download_status_message(message=message):
            self._show_primary_status_message(message)
            return

        fallback_status_message = (
            None if self._download_controller.is_active else DEFAULT_STATUS_MESSAGE
        )
        self._show_transient_status_message(
            message,
            fallback_status_message=fallback_status_message,
        )

    def _show_primary_status_message(self, message: str) -> None:
        self._footer_status_presenter.show_primary(message=message)

    def _show_transient_status_message(
        self,
        message: str,
        *,
        fallback_status_message: str | None = None,
    ) -> None:
        self._footer_status_presenter.show_transient(
            message=message,
            fallback_status_message=fallback_status_message,
        )

    def _confirm_clear_queue(self) -> bool:
        return confirm_dangerous_action(
            parent=self,
            title=CLEAR_QUEUE_CONFIRMATION_TITLE,
            text=CLEAR_QUEUE_CONFIRMATION_TEXT,
            informative_text=CLEAR_QUEUE_CONFIRMATION_DETAILS,
            confirm_button_text=CLEAR_QUEUE_CONFIRMATION_BUTTON,
        )

    def _confirm_delete_cookies(self) -> bool:
        return confirm_dangerous_action(
            parent=self,
            title=DELETE_COOKIES_CONFIRMATION_TITLE,
            text=DELETE_COOKIES_CONFIRMATION_TEXT,
            informative_text=DELETE_COOKIES_CONFIRMATION_DETAILS,
            confirm_button_text=DELETE_COOKIES_CONFIRMATION_BUTTON,
        )

    def _confirm_clear_history(self) -> bool:
        return confirm_dangerous_action(
            parent=self,
            title=CLEAR_HISTORY_CONFIRMATION_TITLE,
            text=CLEAR_HISTORY_CONFIRMATION_TEXT,
            informative_text=CLEAR_HISTORY_CONFIRMATION_DETAILS,
            confirm_button_text=CLEAR_HISTORY_CONFIRMATION_BUTTON,
        )

    def _open_directory(self, *, directory: Path) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    def _update_downloads_dir_label(self) -> None:
        self._settings_panel.set_downloads_dir(downloads_dir=self._settings.downloads_dir)

    def _sync_queue_controls_state(self) -> None:
        has_tasks = self._queue_table.has_tasks()
        has_selected_tasks = bool(self._queue_table.get_selected_task_ids())
        has_downloadable_tasks = bool(
            self._container.download_queue_service.list_downloadable_tasks()
        )
        has_active_download = self._download_controller.is_active

        self._input_panel.add_to_queue_button.setEnabled(not has_active_download)
        self._settings_panel.choose_downloads_dir_button.setEnabled(not has_active_download)
        self._environment_panel.delete_cookies_button.setEnabled(not has_active_download)
        self._environment_panel.refresh_button.setEnabled(not has_active_download)
        self._environment_panel.open_cookies_dir_button.setEnabled(not has_active_download)
        self._environment_panel.open_downloads_dir_button.setEnabled(not has_active_download)

        self._start_queue_button.setEnabled(has_active_download or has_downloadable_tasks)
        self._remove_from_queue_button.setEnabled(has_selected_tasks and not has_active_download)
        self._clear_queue_button.setEnabled(has_tasks and not has_active_download)
        self._sync_start_queue_button_state()

    def _sync_start_queue_button_state(self) -> None:
        if self._download_controller.is_active:
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
