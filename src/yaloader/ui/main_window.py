from __future__ import annotations

from pathlib import Path
from typing import override
from uuid import UUID

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QTimer,
    QTimerEvent,
    QUrl,
    QVariantAnimation,
)
from PyQt6.QtGui import QCloseEvent, QDesktopServices, QShowEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.browser_cookies import BrowserId
from yaloader.application.dto.download_history_record import DownloadHistoryRecord
from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.dto.tool_installation import ToolUpdateCheckResult
from yaloader.application.dto.ytdlp_runtime import YtDlpRuntimeSource
from yaloader.config.app_info import APP_DISPLAY_NAME
from yaloader.domain.download_speed_limit import format_download_speed_limit_label
from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.domain.source_platform import SourcePlatform, detect_source_platform
from yaloader.infrastructure.windows.explorer import reveal_path_in_file_manager
from yaloader.infrastructure.ytdlp.runtime_manager import get_bundled_ytdlp_version
from yaloader.services.app_container import AppContainer
from yaloader.ui.controllers.app_update_controller import (
    AppUpdateController,
    AppUpdateControllerUpdate,
)
from yaloader.ui.controllers.browser_cookies_controller import (
    BrowserCookiesController,
    BrowserCookiesControllerUpdate,
)
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
from yaloader.ui.controllers.platform_icon_controller import PlatformIconController
from yaloader.ui.controllers.queue_input_controller import (
    QueueInputController,
    QueueInputControllerUpdate,
)
from yaloader.ui.controllers.tool_installation_controller import (
    ToolInstallationController,
    ToolInstallationControllerUpdate,
)
from yaloader.ui.controllers.ytdlp_runtime_controller import (
    YtDlpRuntimeController,
    YtDlpRuntimeControllerUpdate,
)
from yaloader.ui.footer_status_presenter import FooterStatusPresenter
from yaloader.ui.status_messages import (
    DEFAULT_STATUS_MESSAGE,
    is_primary_download_status_message,
)
from yaloader.ui.tool_update_confirmation import build_tool_update_confirmation_text
from yaloader.ui.tool_update_dialog import (
    ToolUpdateDialogAction,
    build_managed_tool_update_started_message,
    choose_tool_update_action,
)
from yaloader.ui.widgets.app_header import AppHeader
from yaloader.ui.widgets.common.confirmation_dialogs import (
    confirm_dangerous_action,
    confirm_informational_action,
)
from yaloader.ui.widgets.download_input_panel import DownloadInputPanel
from yaloader.ui.widgets.download_queue.panel import DownloadQueuePanel
from yaloader.ui.widgets.environment_panel import EnvironmentPanel
from yaloader.ui.widgets.history.panel import HISTORY_PANEL_WIDTH, HistoryPanel
from yaloader.ui.widgets.settings_panel import SettingsPanel
from yaloader.ui.widgets.speed_limit_indicator import (
    SPEED_LIMIT_INDICATOR_EXPANDED_HEIGHT,
    SpeedLimitIndicatorPanel,
)
from yaloader.ui.widgets.speed_settings_dialog import (
    SpeedSettingsDialog,
    normalize_download_speed_limit_signal_value,
)
from yaloader.ui.ytdlp_runtime_dialogs import (
    YtDlpFailureRecoveryAction,
    choose_ytdlp_failure_recovery_action,
    confirm_reset_ytdlp_runtime,
)

WINDOW_INITIAL_WIDTH = 1180
WINDOW_INITIAL_HEIGHT = 872
WINDOW_MINIMUM_WIDTH = 1040
WINDOW_MINIMUM_HEIGHT = 820

DOWNLOAD_POLL_INTERVAL_MS = 250
SPEED_LIMIT_INDICATOR_WINDOW_DELTA = SPEED_LIMIT_INDICATOR_EXPANDED_HEIGHT
SPEED_LIMIT_INDICATOR_ANIMATION_DURATION_MS = 165
HISTORY_PANEL_ANIMATION_DURATION_MS = 180
ROW_SELECTION_MODE_STATUS_MESSAGE = "Режим выделения строк активирован"
HISTORY_LINK_COPIED_STATUS_MESSAGE = "Ссылка из истории загрузок скопирована"

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

IMPORT_COOKIES_DIALOG_TITLE = "Выберите cookies.txt"
IMPORT_COOKIES_DIALOG_FILTER = "Cookies files (*.txt);;All files (*)"
REPLACE_COOKIES_CONFIRMATION_TITLE = "Заменить cookies.txt?"
REPLACE_COOKIES_CONFIRMATION_TEXT = "Текущий cookies.txt будет заменён выбранным файлом."
REPLACE_COOKIES_CONFIRMATION_DETAILS = (
    "Используйте только файл, который вы получили из своего браузера или yt-dlp. "
    "Не импортируйте чужие cookies."
)
REPLACE_COOKIES_CONFIRMATION_BUTTON = "Заменить cookies.txt"

FIREFOX_COOKIES_INFO_TITLE = "Создание cookies.txt из Firefox"
FIREFOX_COOKIES_INFO_TEXT = "Перед созданием cookies.txt откройте Firefox и войдите в YouTube."
FIREFOX_COOKIES_INFO_DETAILS = (
    "YaLoader возьмёт cookies из вашего локального профиля Firefox. "
    "Если вход в YouTube не выполнен, файл может создаться, но YouTube всё равно "
    "может запрашивать подтверждение или ограничивать загрузку."
)
FIREFOX_COOKIES_INFO_BUTTON = "Продолжить"

OPERA_COOKIES_INFO_TITLE = "Создание cookies.txt из Opera"
OPERA_COOKIES_INFO_TEXT = "Перед созданием cookies.txt откройте Opera и войдите в YouTube."
OPERA_COOKIES_INFO_DETAILS = (
    "YaLoader возьмёт cookies из вашего локального профиля Opera. "
    "Если вход в YouTube не выполнен, файл может создаться, но YouTube всё равно "
    "может запрашивать подтверждение или ограничивать загрузку."
)
OPERA_COOKIES_INFO_BUTTON = "Продолжить"

CHROME_COOKIES_INFO_TITLE = "Создание cookies.txt из Chrome"
CHROME_COOKIES_INFO_TEXT = "Перед созданием cookies.txt откройте Chrome и войдите в YouTube."
CHROME_COOKIES_INFO_DETAILS = (
    "YaLoader возьмёт cookies из вашего локального профиля Chrome. "
    "Если Chrome запущен или профиль заблокирован, экспорт может не пройти. "
    "В таком случае закройте Chrome полностью и повторите попытку."
)
CHROME_COOKIES_INFO_BUTTON = "Продолжить"

YANDEX_COOKIES_INFO_TITLE = "Создание cookies.txt из Яндекс Браузера"
YANDEX_COOKIES_INFO_TEXT = (
    "Перед созданием cookies.txt откройте Яндекс Браузер и войдите в YouTube."
)
YANDEX_COOKIES_INFO_DETAILS = (
    "YaLoader возьмёт cookies из вашего локального профиля Яндекс Браузера. "
    "Технически yt-dlp будет читать его как Chromium-профиль через browser id chrome. "
    "Если экспорт не пройдёт, полностью закройте Яндекс Браузер и повторите попытку."
)
YANDEX_COOKIES_INFO_BUTTON = "Продолжить"


CLEAR_HISTORY_CONFIRMATION_TITLE = "Очистить историю?"
CLEAR_HISTORY_CONFIRMATION_TEXT = "История загрузок будет полностью очищена."
CLEAR_HISTORY_CONFIRMATION_DETAILS = (
    "Записи истории будут удалены из YaLoader. Скачанные файлы на диске не удаляются."
)
CLEAR_HISTORY_CONFIRMATION_BUTTON = "Очистить историю"


class MainWindow(QMainWindow):
    def __init__(self, container: AppContainer, *, title_font_family: str) -> None:
        super().__init__()

        self._container = container
        self._settings = container.settings

        self._header = AppHeader(self, title_font_family=title_font_family)
        self._speed_limit_indicator = SpeedLimitIndicatorPanel(self)
        self._speed_settings_dialog = SpeedSettingsDialog(self)
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
        self._tool_installation_progress_bar = QProgressBar(self)
        self._footer_status_presenter = FooterStatusPresenter(
            label=self._status_label,
            progress_bar=self._tool_installation_progress_bar,
            parent=self,
        )

        self._metadata_controller = MediaMetadataController(
            service=container.media_metadata_service,
        )
        self._platform_icon_controller = PlatformIconController(
            resolver=container.platform_icon_resolver,
        )
        self._download_controller = DownloadController(
            queue_service=container.download_queue_service,
            history_service=container.download_history_service,
            downloader=container.downloader,
            download_preparer=container.download_preparer,
            prepared_download_cache=container.prepared_download_cache,
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
        self._browser_cookies_controller = BrowserCookiesController(
            service=container.browser_cookies_service,
        )
        self._tool_installation_controller = ToolInstallationController(
            service=container.tool_installation_service,
        )
        self._ytdlp_runtime_controller = YtDlpRuntimeController(
            service=container.ytdlp_runtime_service,
        )
        self._app_update_controller = AppUpdateController(
            service=container.app_update_service,
        )

        self._is_history_panel_visible = self._settings.show_history_on_startup
        self._history_animation: QVariantAnimation | None = None
        self._speed_limit_indicator_animation: QVariantAnimation | None = None
        self._speed_limit_indicator_animation_should_hide = False
        self._is_speed_limit_indicator_expanded = False
        self._is_speed_limit_window_extra_applied = False
        self._speed_limit_indicator_start_height = 0
        self._speed_limit_indicator_end_height = 0
        self._speed_limit_indicator_start_window_height = 0
        self._speed_limit_indicator_end_window_height = 0
        self._speed_limit_indicator_start_queue_height = 0
        self._speed_limit_indicator_end_queue_height = 0
        self._speed_limit_indicator_uses_window_resize = True
        self._speed_limit_indicator_queue_panel_limits: tuple[int, int] | None = None
        self._speed_limit_indicator_frozen_widget_limits: tuple[tuple[QWidget, int, int], ...] = ()
        self._history_animation_start_panel_width = 0
        self._history_animation_end_panel_width = 0
        self._history_animation_start_window_width = 0
        self._history_animation_end_window_width = 0
        self._history_animation_uses_window_resize = True
        self._tool_installation_activity_message: str | None = None
        self._browser_cookies_activity_message: str | None = None
        self._is_combined_tool_update_check_pending = False
        self._pending_managed_tool_update_checks: tuple[ToolUpdateCheckResult, ...] | None = None
        self._pending_ytdlp_update_check: ToolUpdateCheckResult | None = None
        self._download_poll_timer = self.startTimer(DOWNLOAD_POLL_INTERVAL_MS)

        self._configure_window()
        self._configure_widgets()
        self._connect_signals()
        self.setCentralWidget(self._build_central_widget())

        self._update_settings_panel()
        self._apply_environment_update(
            update=self._environment_controller.load_status(
                downloads_dir=self._settings.downloads_dir,
            )
        )
        self._apply_app_update(update=self._app_update_controller.check_update())
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
            self._handle_speed_limit_indicator_window_state_changed()
            self._handle_history_panel_window_state_changed()
            QTimer.singleShot(0, self._handle_speed_limit_indicator_window_state_changed)
            QTimer.singleShot(0, self._handle_history_panel_window_state_changed)
            self._focus_url_input_later()

    def _handle_history_panel_window_state_changed(self) -> None:
        if self._history_animation is not None:
            self._history_animation.stop()
            self._history_animation = None

        target_width = HISTORY_PANEL_WIDTH if self._is_history_panel_visible else 0
        self._history_animation_uses_window_resize = self._should_resize_window_for_history_panel()
        self._history_panel.set_drawer_width(width=target_width)
        self._history_panel.setVisible(self._is_history_panel_visible)
        self._header.set_history_visible(is_visible=self._is_history_panel_visible)
        self._apply_history_minimum_width_for_current_state(history_panel_width=target_width)

        central_widget = self.centralWidget()

        if central_widget is not None:
            central_widget.updateGeometry()

    def _handle_speed_limit_indicator_window_state_changed(self) -> None:
        if self._speed_limit_indicator_animation is not None:
            self._speed_limit_indicator_animation.stop()
            self._speed_limit_indicator_animation = None

        self._release_speed_limit_indicator_animation_widgets()
        self._speed_limit_indicator_uses_window_resize = (
            self._should_resize_window_for_speed_limit_indicator()
        )

        if self._speed_limit_indicator.is_expanded():
            self._speed_limit_indicator.set_expanded()
            self._is_speed_limit_window_extra_applied = True

            if self._speed_limit_indicator_uses_window_resize:
                self.setMinimumHeight(WINDOW_MINIMUM_HEIGHT + SPEED_LIMIT_INDICATOR_WINDOW_DELTA)
            else:
                self.setMinimumHeight(WINDOW_MINIMUM_HEIGHT)
        else:
            self._speed_limit_indicator.set_collapsed()
            self._is_speed_limit_window_extra_applied = False
            self.setMinimumHeight(WINDOW_MINIMUM_HEIGHT)

        self._queue_panel.updateGeometry()

    @override
    def closeEvent(self, event: QCloseEvent | None) -> None:
        self._footer_status_presenter.shutdown()
        self.killTimer(self._download_poll_timer)
        self._download_controller.shutdown()
        self._metadata_controller.shutdown()
        self._platform_icon_controller.shutdown()
        self._browser_cookies_controller.shutdown()
        self._tool_installation_controller.shutdown()
        self._ytdlp_runtime_controller.shutdown()
        self._app_update_controller.shutdown()
        super().closeEvent(event)

    @override
    def timerEvent(self, event: QTimerEvent | None) -> None:
        if event is not None and event.timerId() != self._download_poll_timer:
            super().timerEvent(event)
            return

        self._drain_platform_icon_events()
        self._drain_metadata_events()
        self._apply_download_update(update=self._download_controller.poll())
        self._apply_tool_installation_update(
            update=self._tool_installation_controller.poll(),
        )
        self._apply_ytdlp_runtime_update(
            update=self._ytdlp_runtime_controller.poll(),
        )
        self._apply_browser_cookies_update(
            update=self._browser_cookies_controller.poll(),
        )
        self._apply_app_update(update=self._app_update_controller.poll())

    def _configure_window(self) -> None:
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(WINDOW_INITIAL_WIDTH, WINDOW_INITIAL_HEIGHT)
        self.setMinimumSize(WINDOW_MINIMUM_WIDTH, WINDOW_MINIMUM_HEIGHT)
        self._set_history_adjusted_minimum_width(history_panel_width=0)

    def _configure_widgets(self) -> None:
        self._status_label.setObjectName("StatusLabel")
        self._tool_installation_progress_bar.setObjectName("ToolInstallationProgressBar")

        self._queue_table.set_context_menu_callbacks(
            on_download_tasks=self._start_tasks_download,
            on_cancel_tasks=self._cancel_tasks_download,
            on_remove_tasks=self._remove_tasks_from_queue,
        )
        self._queue_table.set_url_drop_callback(
            on_url_dropped=self._handle_queue_url_dropped,
        )
        self._history_panel.set_context_menu_callbacks(
            on_add_to_queue=self._handle_add_history_record_to_queue,
            on_delete_record=self._handle_delete_history_record,
            on_copy_url=self._handle_copy_history_record_url,
        )
        self._sync_start_queue_button_state()

    def _connect_signals(self) -> None:
        self._input_panel.add_to_queue_button.clicked.connect(self._handle_add_to_queue_clicked)
        self._start_queue_button.clicked.connect(self._handle_start_or_cancel_queue_clicked)
        self._remove_from_queue_button.clicked.connect(self._handle_remove_selected_tasks_clicked)
        self._clear_queue_button.clicked.connect(self._handle_clear_queue_clicked)
        self._queue_table.itemSelectionChanged.connect(self._sync_queue_controls_state)
        self._queue_table.row_selection_mode_changed.connect(
            self._handle_row_selection_mode_changed
        )

        self._settings_panel.choose_downloads_dir_button.clicked.connect(
            self._handle_choose_downloads_dir_clicked
        )
        self._settings_panel.set_downloads_dir_clicked_callback(
            self._handle_open_downloads_dir_clicked
        )

        self._speed_settings_dialog.show_history_on_startup_changed.connect(
            self._handle_show_history_on_startup_changed
        )
        self._speed_settings_dialog.open_downloads_dir_after_queue_completed_changed.connect(
            self._handle_open_downloads_dir_after_queue_completed_changed
        )
        self._speed_settings_dialog.confirm_clear_queue_changed.connect(
            self._handle_confirm_clear_queue_changed
        )

        self._speed_settings_dialog.separate_audio_video_enabled_changed.connect(
            self._handle_separate_audio_video_enabled_changed
        )
        self._speed_settings_dialog.separate_audio_video_audio_format_changed.connect(
            self._handle_separate_audio_video_audio_format_changed
        )

        self._header.settings_button.clicked.connect(self._handle_speed_settings_button_clicked)
        self._speed_settings_dialog.download_speed_limit_changed.connect(
            self._handle_download_speed_limit_signal_changed
        )

        self._environment_panel.prepare_system_button.clicked.connect(
            self._handle_prepare_system_clicked
        )
        self._environment_panel.update_tools_button.clicked.connect(
            self._handle_update_tools_clicked
        )
        self._environment_panel.connect_ytdlp_reset_requested(self._handle_reset_ytdlp_clicked)
        self._environment_panel.import_cookies_action.triggered.connect(
            self._handle_import_cookies_clicked
        )
        self._environment_panel.export_firefox_cookies_action.triggered.connect(
            self._handle_export_firefox_cookies_clicked
        )
        self._environment_panel.export_opera_cookies_action.triggered.connect(
            self._handle_export_opera_cookies_clicked
        )
        self._environment_panel.export_chrome_cookies_action.triggered.connect(
            self._handle_export_chrome_cookies_clicked
        )
        self._environment_panel.export_yandex_cookies_action.triggered.connect(
            self._handle_export_yandex_cookies_clicked
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
        root_layout.setSpacing(14)

        root_layout.addWidget(self._header)
        root_layout.addWidget(self._input_panel)
        root_layout.addWidget(self._queue_panel, stretch=1)
        root_layout.addWidget(self._build_settings_stack_widget())
        root_layout.addWidget(self._environment_panel)
        root_layout.addWidget(self._build_footer())

        return main_content_widget

    def _build_settings_stack_widget(self) -> QWidget:
        settings_stack_widget = QWidget(self)
        settings_stack_layout = QVBoxLayout(settings_stack_widget)
        settings_stack_layout.setContentsMargins(0, 0, 0, 0)
        settings_stack_layout.setSpacing(0)

        settings_stack_layout.addWidget(self._settings_panel)
        settings_stack_layout.addWidget(self._speed_limit_indicator)

        return settings_stack_widget

    def _build_footer(self) -> QWidget:
        footer = QWidget(self)
        footer.setObjectName("FooterWidget")

        root_layout = QVBoxLayout(footer)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(6)

        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(0)
        status_layout.addWidget(self._status_label)
        status_layout.addStretch(1)

        root_layout.addLayout(status_layout)
        root_layout.addWidget(self._tool_installation_progress_bar)

        return footer

    def _toggle_history_panel(self) -> None:
        self._animate_history_panel_visibility(
            is_visible=not self._is_history_panel_visible,
        )

    def _sync_history_panel_visibility(self) -> None:
        target_width = HISTORY_PANEL_WIDTH if self._is_history_panel_visible else 0
        self._history_panel.set_drawer_width(width=target_width)
        self._history_panel.setVisible(self._is_history_panel_visible)
        self._header.set_history_visible(is_visible=self._is_history_panel_visible)
        self._apply_history_minimum_width_for_current_state(history_panel_width=target_width)

    def _set_history_adjusted_minimum_width(self, *, history_panel_width: int) -> None:
        self.setMinimumWidth(
            calculate_history_adjusted_window_minimum_width(
                history_panel_width=history_panel_width,
            )
        )

    def _animate_history_panel_visibility(self, *, is_visible: bool) -> None:
        current_panel_width = self._history_panel.current_drawer_width()
        start_window_width = self.width()

        if self._history_animation is not None:
            self._history_animation.stop()
            self._history_animation = None

        self._history_animation_uses_window_resize = self._should_resize_window_for_history_panel()

        if is_visible:
            remaining_panel_width = HISTORY_PANEL_WIDTH - current_panel_width
            target_window_width = (
                start_window_width + remaining_panel_width
                if self._history_animation_uses_window_resize
                else start_window_width
            )

            self._is_history_panel_visible = True
            self._history_panel.setVisible(True)
            self._header.set_history_visible(is_visible=True)
            self._start_history_panel_width_animation(
                start_panel_width=current_panel_width,
                end_panel_width=HISTORY_PANEL_WIDTH,
                start_window_width=start_window_width,
                end_window_width=max(
                    self._calculate_history_window_target_width(
                        history_panel_width=HISTORY_PANEL_WIDTH,
                        target_window_width=target_window_width,
                    ),
                    target_window_width,
                ),
                hide_after_finish=False,
            )
            return

        target_window_width = (
            start_window_width - current_panel_width
            if self._history_animation_uses_window_resize
            else start_window_width
        )

        self._is_history_panel_visible = False
        self._header.set_history_visible(is_visible=False)
        self._start_history_panel_width_animation(
            start_panel_width=current_panel_width,
            end_panel_width=0,
            start_window_width=start_window_width,
            end_window_width=max(
                self._calculate_history_window_target_width(
                    history_panel_width=0,
                    target_window_width=target_window_width,
                ),
                target_window_width,
            ),
            hide_after_finish=True,
        )

    def _start_history_panel_width_animation(
        self,
        *,
        start_panel_width: int,
        end_panel_width: int,
        start_window_width: int,
        end_window_width: int,
        hide_after_finish: bool,
    ) -> None:
        self._apply_history_minimum_width_for_current_state(
            history_panel_width=start_panel_width,
        )

        self._history_animation_start_panel_width = start_panel_width
        self._history_animation_end_panel_width = end_panel_width
        self._history_animation_start_window_width = start_window_width
        self._history_animation_end_window_width = end_window_width

        animation = QVariantAnimation(self)
        animation.setDuration(HISTORY_PANEL_ANIMATION_DURATION_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.valueChanged.connect(self._handle_history_panel_width_animation_value_changed)
        animation.finished.connect(
            lambda: self._handle_history_panel_width_animation_finished(
                hide_after_finish=hide_after_finish,
            )
        )

        self._history_animation = animation
        animation.start()

    def _handle_history_panel_width_animation_value_changed(self, value: object) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return

        progress = max(0.0, min(1.0, float(value)))
        panel_width = round(
            self._history_animation_start_panel_width
            + (self._history_animation_end_panel_width - self._history_animation_start_panel_width)
            * progress
        )
        window_width = round(
            self._history_animation_start_window_width
            + (
                self._history_animation_end_window_width
                - self._history_animation_start_window_width
            )
            * progress
        )

        self._history_panel.set_drawer_width(width=panel_width)
        self._apply_history_minimum_width_for_current_state(history_panel_width=panel_width)

        if self._history_animation_uses_window_resize:
            self.resize(max(self.minimumWidth(), window_width), self.height())
            return

        central_widget = self.centralWidget()

        if central_widget is not None:
            central_widget.updateGeometry()

    def _handle_history_panel_width_animation_finished(self, *, hide_after_finish: bool) -> None:
        if hide_after_finish:
            final_panel_width = 0
            self._history_panel.set_drawer_width(width=final_panel_width)
            self._history_panel.setVisible(False)
        else:
            final_panel_width = HISTORY_PANEL_WIDTH
            self._history_panel.set_drawer_width(width=final_panel_width)

        self._apply_history_minimum_width_for_current_state(
            history_panel_width=final_panel_width,
        )

        if self._history_animation_uses_window_resize:
            self.resize(
                max(self.minimumWidth(), self._history_animation_end_window_width),
                self.height(),
            )

        self._history_animation = None

    def _calculate_history_window_target_width(
        self,
        *,
        history_panel_width: int,
        target_window_width: int,
    ) -> int:
        if not self._history_animation_uses_window_resize:
            return target_window_width

        return calculate_history_adjusted_window_minimum_width(
            history_panel_width=history_panel_width,
        )

    def _apply_history_minimum_width_for_current_state(
        self,
        *,
        history_panel_width: int,
    ) -> None:
        if self._should_resize_window_for_history_panel():
            self._set_history_adjusted_minimum_width(history_panel_width=history_panel_width)
            return

        self.setMinimumWidth(WINDOW_MINIMUM_WIDTH)

    def _should_resize_window_for_history_panel(self) -> bool:
        return not (self.isMaximized() or self.isFullScreen())

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
        self._apply_history_update(
            update=self._history_controller.add_record_to_queue(record=record)
        )

    def _handle_delete_history_record(self, record: DownloadHistoryRecord) -> None:
        self._apply_history_update(update=self._history_controller.remove_record(record=record))

    def _handle_copy_history_record_url(self, _record: DownloadHistoryRecord) -> None:
        self._show_transient_status_message(HISTORY_LINK_COPIED_STATUS_MESSAGE)

    def _apply_history_update(self, *, update: HistoryControllerUpdate) -> None:
        if update.records is not None:
            self._history_panel.set_records(records=update.records)

        if update.should_clear_download_history_flags:
            self._download_controller.clear_recorded_history_flags()

        if update.added_task is not None:
            self._queue_table.append_task(task=update.added_task)
            self._start_platform_icon_resolution_if_needed(task=update.added_task)

        if update.added_task is not None and update.metadata_request is not None:
            self._start_metadata_resolution(
                task_id=update.added_task.task_id,
                request=update.metadata_request,
            )

        if update.status_message is not None:
            self._show_transient_status_message(update.status_message)

        self._sync_queue_controls_state()

    def _start_platform_icon_resolution_if_needed(self, *, task: DownloadTask) -> None:
        if detect_source_platform(url=task.url.value) is not SourcePlatform.UNKNOWN:
            return

        self._platform_icon_controller.start_resolution(
            task_id=task.task_id,
            url=task.url.value,
        )

    def _drain_platform_icon_events(self) -> None:
        for result in self._platform_icon_controller.drain_results():
            if result.icon_path is None:
                continue

            self._queue_table.set_platform_icon_path(
                task_id=result.task_id,
                icon_path=result.icon_path,
            )

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
            self._queue_table.mark_metadata_resolution_pending(task_id=task_id)

    def _drain_metadata_events(self) -> None:
        for result in self._metadata_controller.drain_results():
            self._apply_metadata_result(result=result)

    def _apply_metadata_result(self, *, result: MediaMetadataResolutionResult) -> None:
        self._queue_table.clear_metadata_resolution_pending(task_id=result.task_id)

        if result.metadata is None:
            self._queue_table.mark_metadata_resolution_failed(task_id=result.task_id)
            self._show_transient_status_message(
                "Не удалось определить данные медиа. yt-dlp попробует скачать напрямую"
            )
            return

        updated_task = self._container.download_queue_service.apply_metadata(
            task_id=result.task_id,
            title=result.metadata.title,
            video_quality=result.metadata.resolved_video_quality,
            playlist_count=result.metadata.playlist_count,
            duration_seconds=result.metadata.duration_seconds,
            estimated_file_size_bytes=result.metadata.estimated_file_size_bytes,
            is_file_size_estimated=result.metadata.is_file_size_estimated,
        )

        if updated_task is None:
            return

        if updated_task.status is DownloadStatus.RUNNING:
            return

        self._queue_table.update_task(task=updated_task)

        if updated_task.mode is DownloadMode.AUDIO:
            self._show_transient_status_message("Данные аудио определены")
            return

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
                separate_audio_video_enabled=self._settings.separate_audio_video_enabled,
                separate_audio_format=self._settings.separate_audio_video_audio_format,
                download_speed_limit_bytes_per_second=(
                    self._settings.download_speed_limit_bytes_per_second
                ),
            )
        )

    def _handle_queue_url_dropped(self, url: str) -> None:
        self._apply_queue_input_update(
            update=self._queue_input_controller.add_from_input(
                url=url,
                target_dir=self._settings.downloads_dir,
                output_format=self._input_panel.get_selected_output_format(),
                video_quality=self._input_panel.get_selected_video_quality(),
                separate_audio_video_enabled=self._settings.separate_audio_video_enabled,
                separate_audio_format=self._settings.separate_audio_video_audio_format,
                download_speed_limit_bytes_per_second=(
                    self._settings.download_speed_limit_bytes_per_second
                ),
            ),
            should_apply_input_feedback=False,
        )

    def _apply_queue_input_update(
        self,
        *,
        update: QueueInputControllerUpdate,
        should_apply_input_feedback: bool = True,
    ) -> None:
        if update.added_task is not None:
            self._queue_table.append_task(task=update.added_task)
            self._start_platform_icon_resolution_if_needed(task=update.added_task)

        if update.added_task is not None and update.metadata_request is not None:
            self._start_metadata_resolution(
                task_id=update.added_task.task_id,
                request=update.metadata_request,
            )

        if should_apply_input_feedback and update.should_clear_url_input:
            self._input_panel.clear_url()

        if update.status_message is not None:
            self._show_transient_status_message(update.status_message)

        self._sync_queue_controls_state()

        if should_apply_input_feedback and update.should_focus_url_input:
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

    def _handle_speed_settings_button_clicked(self) -> None:
        self._speed_settings_dialog.toggle_near_anchor(
            anchor_widget=self._header.settings_button,
            bytes_per_second=self._settings.download_speed_limit_bytes_per_second,
            settings=self._settings,
        )

    def _handle_separate_audio_video_enabled_changed(self, is_enabled: bool) -> None:
        update = self._environment_controller.change_separate_audio_video_enabled(
            is_enabled=is_enabled,
        )
        self._apply_environment_update(update=update)

    def _handle_separate_audio_video_audio_format_changed(
        self,
        audio_format: OutputFormat,
    ) -> None:
        update = self._environment_controller.change_separate_audio_video_audio_format(
            audio_format=audio_format,
        )
        self._apply_environment_update(update=update)

    def _handle_download_speed_limit_signal_changed(self, value: object) -> None:
        try:
            selected_speed_limit = normalize_download_speed_limit_signal_value(value)
        except ValueError as error:
            self._show_transient_status_message(
                f"Некорректное ограничение скорости: {error}",
            )
            return

        self._apply_download_speed_limit_change(bytes_per_second=selected_speed_limit)

    def _apply_download_speed_limit_change(self, *, bytes_per_second: int | None) -> None:
        environment_update = self._environment_controller.change_download_speed_limit(
            bytes_per_second=bytes_per_second,
        )
        self._apply_environment_update(update=environment_update)

        if environment_update.settings is None:
            return

        self._container.download_speed_limit_state.set_download_speed_limit_bytes_per_second(
            bytes_per_second=bytes_per_second,
        )

        queue_service = self._container.download_queue_service
        updated_tasks = queue_service.update_download_speed_limit_for_mutable_tasks(
            bytes_per_second=bytes_per_second,
        )

        if updated_tasks:
            self._queue_table.reload_tasks(queue_service.list_tasks())

        self._show_transient_status_message(
            "Лимит скорости загрузки обновлён: "
            f"{format_download_speed_limit_label(bytes_per_second=bytes_per_second)}"
        )

    def _handle_export_firefox_cookies_clicked(self) -> None:
        if not self._confirm_firefox_youtube_login():
            return

        if self._container.paths.cookies_file.is_file() and not self._confirm_replace_cookies():
            return

        self._apply_browser_cookies_update(
            update=self._browser_cookies_controller.start_export_from_browser(
                browser_id=BrowserId.FIREFOX,
            )
        )

    def _handle_export_opera_cookies_clicked(self) -> None:
        if not self._confirm_opera_youtube_login():
            return

        if self._container.paths.cookies_file.is_file() and not self._confirm_replace_cookies():
            return

        self._apply_browser_cookies_update(
            update=self._browser_cookies_controller.start_export_from_browser(
                browser_id=BrowserId.OPERA,
            )
        )

    def _handle_export_chrome_cookies_clicked(self) -> None:
        if not self._confirm_chrome_youtube_login():
            return

        if self._container.paths.cookies_file.is_file() and not self._confirm_replace_cookies():
            return

        self._apply_browser_cookies_update(
            update=self._browser_cookies_controller.start_export_from_browser(
                browser_id=BrowserId.CHROME,
            )
        )

    def _handle_export_yandex_cookies_clicked(self) -> None:
        if not self._confirm_yandex_youtube_login():
            return

        if self._container.paths.cookies_file.is_file() and not self._confirm_replace_cookies():
            return

        self._apply_browser_cookies_update(
            update=self._browser_cookies_controller.start_export_from_browser(
                browser_id=BrowserId.YANDEX,
            )
        )

    def _handle_import_cookies_clicked(self) -> None:
        selected_file, _selected_filter = QFileDialog.getOpenFileName(
            self,
            IMPORT_COOKIES_DIALOG_TITLE,
            str(self._container.paths.data_dir),
            IMPORT_COOKIES_DIALOG_FILTER,
        )

        if not selected_file:
            return

        source_file = Path(selected_file)

        if (
            self._container.paths.cookies_file.is_file()
            and not is_same_filesystem_path(
                left_path=source_file,
                right_path=self._container.paths.cookies_file,
            )
            and not self._confirm_replace_cookies()
        ):
            return

        self._apply_environment_update(
            update=self._environment_controller.import_cookies(
                source_file=source_file,
                downloads_dir=self._settings.downloads_dir,
            )
        )

    def _handle_show_history_on_startup_changed(self, is_checked: bool) -> None:
        self._apply_environment_update(
            update=self._environment_controller.change_show_history_on_startup(
                is_enabled=is_checked,
            )
        )

        if self._is_history_panel_visible == is_checked:
            return

        if self.isVisible():
            self._animate_history_panel_visibility(is_visible=is_checked)
            return

        self._is_history_panel_visible = is_checked
        self._sync_history_panel_visibility()

    def _handle_open_downloads_dir_after_queue_completed_changed(
        self,
        is_checked: bool,
    ) -> None:
        self._apply_environment_update(
            update=self._environment_controller.change_open_downloads_dir_after_queue_completed(
                is_enabled=is_checked,
            )
        )

    def _handle_confirm_clear_queue_changed(self, is_checked: bool) -> None:
        self._apply_environment_update(
            update=self._environment_controller.change_confirm_clear_queue(
                is_enabled=is_checked,
            )
        )

    def _handle_update_tools_clicked(self) -> None:
        if self._tool_installation_controller.is_active or self._ytdlp_runtime_controller.is_active:
            self._show_transient_status_message(
                "Проверка или обновление инструментов уже выполняется"
            )
            return

        self._is_combined_tool_update_check_pending = True
        self._pending_managed_tool_update_checks = None
        self._pending_ytdlp_update_check = None

        self._apply_tool_installation_update(
            update=self._tool_installation_controller.check_required_tools_updates(),
        )
        self._apply_ytdlp_runtime_update(
            update=self._ytdlp_runtime_controller.check_update(),
        )

    def _handle_reset_ytdlp_clicked(self) -> None:
        if not confirm_reset_ytdlp_runtime(parent=self):
            self._show_transient_status_message("Сброс yt-dlp отменён")
            return

        self._apply_ytdlp_runtime_update(
            update=self._ytdlp_runtime_controller.reset_to_bundled(),
        )

    def _handle_prepare_system_clicked(self) -> None:
        self._apply_tool_installation_update(
            update=self._tool_installation_controller.start_required_tools_installation(),
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

    def _apply_app_update(self, *, update: AppUpdateControllerUpdate) -> None:
        if update.status_message is not None:
            self._show_transient_status_message(update.status_message)

        if update.result is None:
            return

        if update.result.should_update and update.result.latest_version is not None:
            self._header.set_application_update_available(
                latest_version=update.result.latest_version,
                releases_url=update.result.releases_url,
            )
            self._show_transient_status_message(update.result.message)
            return

        if not update.result.is_success:
            self._show_transient_status_message(update.result.message)

    def _apply_environment_update(self, *, update: EnvironmentControllerUpdate) -> None:
        if update.settings is not None:
            self._settings = update.settings
            self._update_settings_panel()

        if update.environment_status is not None:
            self._environment_panel.set_status(status=update.environment_status)

            if not update.environment_status.downloads_dir.is_ok:
                self._show_transient_status_message(
                    f"Папка загрузок: {update.environment_status.downloads_dir.message}"
                )

        if update.should_play_refresh_feedback:
            self._environment_panel.play_refresh_feedback()

        if update.directory_to_open is not None:
            self._open_directory(directory=update.directory_to_open)

        if update.status_message is not None:
            self._show_transient_status_message(update.status_message)

        self._sync_queue_controls_state()

    def _apply_browser_cookies_update(
        self,
        *,
        update: BrowserCookiesControllerUpdate,
    ) -> None:
        for progress in update.progress_events:
            self._show_browser_cookies_activity_message(message=progress.message)

        if update.should_refresh_environment_status:
            self._apply_environment_update(
                update=self._environment_controller.load_status(
                    downloads_dir=self._settings.downloads_dir,
                )
            )
            self._environment_panel.play_refresh_feedback()

        if update.status_message is not None:
            if not self._browser_cookies_controller.is_active:
                self._clear_browser_cookies_activity_message()

            self._show_transient_status_message(update.status_message)

        self._sync_queue_controls_state()

    def _show_browser_cookies_activity_message(self, *, message: str) -> None:
        activity_message = f"Cookies: {message}"

        if self._browser_cookies_activity_message is not None:
            self._footer_status_presenter.clear_activity(
                message=self._browser_cookies_activity_message,
            )

        self._browser_cookies_activity_message = activity_message
        self._footer_status_presenter.show_activity(message=activity_message)

    def _clear_browser_cookies_activity_message(self) -> None:
        if self._browser_cookies_activity_message is None:
            return

        self._footer_status_presenter.clear_activity(
            message=self._browser_cookies_activity_message,
        )
        self._browser_cookies_activity_message = None

    def _apply_tool_installation_update(
        self,
        *,
        update: ToolInstallationControllerUpdate,
    ) -> None:
        for progress in update.progress_events:
            self._show_tool_installation_activity_message(
                message=progress.message,
                percent=progress.percent,
            )

        if update.update_checks:
            self._handle_managed_tool_update_checks(update_checks=update.update_checks)
            self._sync_queue_controls_state()
            return

        if update.should_refresh_environment_status:
            self._apply_environment_update(
                update=self._environment_controller.load_status(
                    downloads_dir=self._settings.downloads_dir,
                )
            )
            self._environment_panel.play_refresh_feedback()

        if update.status_message is not None:
            if not self._tool_installation_controller.is_active:
                self._clear_tool_installation_activity_message()

            self._show_transient_status_message(update.status_message)

        self._sync_queue_controls_state()

    def _handle_managed_tool_update_checks(
        self,
        *,
        update_checks: tuple[ToolUpdateCheckResult, ...],
    ) -> None:
        if self._is_combined_tool_update_check_pending:
            self._pending_managed_tool_update_checks = update_checks
            self._try_show_combined_tool_update_dialog()
            return

        confirmation_text = build_tool_update_confirmation_text(update_checks=update_checks)

        if not confirm_informational_action(
            parent=self,
            title=confirmation_text.title,
            text=confirmation_text.text,
            informative_text=confirmation_text.informative_text,
            confirm_button_text=confirmation_text.confirm_button_text,
        ):
            self._show_transient_status_message(confirmation_text.canceled_status_message)
            return

        self._apply_tool_installation_update(
            update=self._tool_installation_controller.start_required_tools_update(
                start_message=confirmation_text.started_status_message,
            ),
        )

    def _try_show_combined_tool_update_dialog(self) -> None:
        if not self._is_combined_tool_update_check_pending:
            return

        if self._pending_managed_tool_update_checks is None:
            return

        if self._pending_ytdlp_update_check is None:
            return

        managed_update_checks = self._pending_managed_tool_update_checks
        ytdlp_update_check = self._pending_ytdlp_update_check

        self._is_combined_tool_update_check_pending = False
        self._pending_managed_tool_update_checks = None
        self._pending_ytdlp_update_check = None

        action = choose_tool_update_action(
            parent=self,
            managed_update_checks=managed_update_checks,
            ytdlp_update_check=ytdlp_update_check,
        )

        if action is ToolUpdateDialogAction.MANAGED_TOOLS:
            self._apply_tool_installation_update(
                update=self._tool_installation_controller.start_required_tools_update(
                    start_message=build_managed_tool_update_started_message(
                        update_checks=managed_update_checks,
                    ),
                ),
            )
            return

        if action is ToolUpdateDialogAction.YTDLP:
            self._apply_ytdlp_runtime_update(
                update=self._ytdlp_runtime_controller.install_latest(),
            )
            return

        self._show_transient_status_message("Обновление инструментов отменено")
        self._handle_refresh_environment_status_clicked()

    def _apply_ytdlp_runtime_update(
        self,
        *,
        update: YtDlpRuntimeControllerUpdate,
    ) -> None:
        for progress in update.progress_events:
            self._show_tool_installation_activity_message(
                message=f"yt-dlp: {progress.message}",
                percent=progress.percent,
            )

        if update.update_check is not None:
            self._handle_ytdlp_update_check_received(update_check=update.update_check)

        if update.should_refresh_environment_status:
            self._apply_environment_update(
                update=self._environment_controller.load_status(
                    downloads_dir=self._settings.downloads_dir,
                )
            )
            self._environment_panel.play_refresh_feedback()

        if update.status_message is not None:
            if not self._ytdlp_runtime_controller.is_active:
                self._clear_tool_installation_activity_message()

            self._show_transient_status_message(update.status_message)

        self._sync_queue_controls_state()

    def _handle_ytdlp_update_check_received(
        self,
        *,
        update_check: ToolUpdateCheckResult,
    ) -> None:
        if update_check.latest_version is not None:
            runtime_info = self._container.ytdlp_runtime_manager.get_runtime_info()
            self._environment_panel.set_ytdlp_update_available(
                latest_version=update_check.latest_version,
                is_external=runtime_info.is_external,
            )

        if self._is_combined_tool_update_check_pending:
            self._pending_ytdlp_update_check = update_check
            self._try_show_combined_tool_update_dialog()
            return

        self._show_transient_status_message(update_check.message)

    def _show_tool_installation_activity_message(
        self,
        *,
        message: str,
        percent: int | None,
    ) -> None:
        activity_message = f"Инструменты: {message}"

        if self._tool_installation_activity_message is not None:
            self._footer_status_presenter.clear_activity(
                message=self._tool_installation_activity_message,
            )

        self._tool_installation_activity_message = activity_message
        self._footer_status_presenter.show_activity(message=activity_message)
        self._footer_status_presenter.show_progress(
            message=message,
            percent=percent,
        )

    def _clear_tool_installation_activity_message(self) -> None:
        if self._tool_installation_activity_message is None:
            return

        self._footer_status_presenter.clear_activity(
            message=self._tool_installation_activity_message,
        )
        self._footer_status_presenter.hide_progress()
        self._tool_installation_activity_message = None

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
        should_confirm_clear_queue = (
            self._settings.confirm_clear_queue and self._queue_table.has_tasks()
        )

        if should_confirm_clear_queue and not self._confirm_clear_queue():
            return

        self._apply_download_update(update=self._download_controller.clear_queue())

    def _start_tasks_download(self, task_ids: tuple[UUID, ...]) -> None:
        self._apply_download_update(update=self._download_controller.start_tasks(task_ids=task_ids))

    def _cancel_tasks_download(self, task_ids: tuple[UUID, ...]) -> None:
        self._apply_download_update(
            update=self._download_controller.cancel_tasks_download(task_ids=task_ids)
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

        if update.prepared_task_ids:
            self._queue_table.prepare_tasks_for_download(
                task_ids=update.prepared_task_ids,
            )

        if update.completed_preparation_task_ids:
            self._queue_table.mark_tasks_prepared_for_download(
                task_ids=update.completed_preparation_task_ids,
            )

        for progress in update.progress_events:
            self._queue_table.set_task_progress(progress=progress)

        if update.should_reload_history:
            self._reload_history_panel()

        if self._should_open_downloads_dir_after_queue_completed(update=update):
            self._open_directory(directory=self._settings.downloads_dir)

        if update.status_message is not None:
            self._apply_download_status_message(message=update.status_message)

        self._maybe_offer_ytdlp_failure_recovery(update=update)

        self._sync_queue_controls_state()

    def _maybe_offer_ytdlp_failure_recovery(
        self,
        *,
        update: DownloadControllerUpdate,
    ) -> None:
        if self._download_controller.is_active:
            return

        failed_task_ids = tuple(
            task.task_id for task in update.updated_tasks if task.status is DownloadStatus.FAILED
        )

        if not failed_task_ids:
            return

        runtime_info = self._container.ytdlp_runtime_manager.get_runtime_info()

        if runtime_info.source is not YtDlpRuntimeSource.EXTERNAL:
            return

        action = choose_ytdlp_failure_recovery_action(
            parent=self,
            external_version=runtime_info.version,
            bundled_version=get_bundled_ytdlp_version(),
        )

        if action is YtDlpFailureRecoveryAction.NONE:
            return

        reset_result = self._container.ytdlp_runtime_service.reset_to_bundled()
        self._show_transient_status_message(reset_result.message)
        self._apply_environment_update(
            update=self._environment_controller.load_status(
                downloads_dir=self._settings.downloads_dir,
            )
        )

        if not reset_result.is_success:
            return

        self._download_controller.clear_prepared_downloads(task_ids=failed_task_ids)

        if action is YtDlpFailureRecoveryAction.TRY_BUNDLED:
            self._apply_download_update(
                update=self._download_controller.start_tasks(task_ids=failed_task_ids),
            )

    def _should_open_downloads_dir_after_queue_completed(
        self,
        *,
        update: DownloadControllerUpdate,
    ) -> bool:
        if not self._settings.open_downloads_dir_after_queue_completed:
            return False

        if update.status_message != "Очередь загрузок завершена":
            return False

        return any(task.status is DownloadStatus.COMPLETED for task in update.updated_tasks)

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

    def _confirm_firefox_youtube_login(self) -> bool:
        return confirm_informational_action(
            parent=self,
            title=FIREFOX_COOKIES_INFO_TITLE,
            text=FIREFOX_COOKIES_INFO_TEXT,
            informative_text=FIREFOX_COOKIES_INFO_DETAILS,
            confirm_button_text=FIREFOX_COOKIES_INFO_BUTTON,
        )

    def _confirm_opera_youtube_login(self) -> bool:
        return confirm_informational_action(
            parent=self,
            title=OPERA_COOKIES_INFO_TITLE,
            text=OPERA_COOKIES_INFO_TEXT,
            informative_text=OPERA_COOKIES_INFO_DETAILS,
            confirm_button_text=OPERA_COOKIES_INFO_BUTTON,
        )

    def _confirm_chrome_youtube_login(self) -> bool:
        return confirm_informational_action(
            parent=self,
            title=CHROME_COOKIES_INFO_TITLE,
            text=CHROME_COOKIES_INFO_TEXT,
            informative_text=CHROME_COOKIES_INFO_DETAILS,
            confirm_button_text=CHROME_COOKIES_INFO_BUTTON,
        )

    def _confirm_yandex_youtube_login(self) -> bool:
        return confirm_informational_action(
            parent=self,
            title=YANDEX_COOKIES_INFO_TITLE,
            text=YANDEX_COOKIES_INFO_TEXT,
            informative_text=YANDEX_COOKIES_INFO_DETAILS,
            confirm_button_text=YANDEX_COOKIES_INFO_BUTTON,
        )

    def _confirm_replace_cookies(self) -> bool:
        return confirm_dangerous_action(
            parent=self,
            title=REPLACE_COOKIES_CONFIRMATION_TITLE,
            text=REPLACE_COOKIES_CONFIRMATION_TEXT,
            informative_text=REPLACE_COOKIES_CONFIRMATION_DETAILS,
            confirm_button_text=REPLACE_COOKIES_CONFIRMATION_BUTTON,
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
        if reveal_path_in_file_manager(path=directory):
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    def _update_settings_panel(self) -> None:
        self._settings_panel.set_downloads_dir(downloads_dir=self._settings.downloads_dir)
        self._speed_settings_dialog.set_download_speed_limit(
            bytes_per_second=self._settings.download_speed_limit_bytes_per_second,
        )
        self._speed_settings_dialog.set_preferences(settings=self._settings)
        self._sync_speed_limit_indicator(
            bytes_per_second=self._settings.download_speed_limit_bytes_per_second,
        )

    def _sync_speed_limit_indicator(self, *, bytes_per_second: int | None) -> None:
        should_show_indicator = bytes_per_second is not None

        self._speed_limit_indicator.set_download_speed_limit(
            bytes_per_second=bytes_per_second,
        )

        if self._is_speed_limit_indicator_expanded == should_show_indicator:
            return

        self._is_speed_limit_indicator_expanded = should_show_indicator

        if not self.isVisible():
            self._apply_speed_limit_indicator_visibility_directly(
                is_visible=should_show_indicator,
            )
            return

        self._animate_speed_limit_indicator_visibility(is_visible=should_show_indicator)

    def _apply_speed_limit_indicator_visibility_directly(self, *, is_visible: bool) -> None:
        if self._speed_limit_indicator_animation is not None:
            self._speed_limit_indicator_animation.stop()
            self._speed_limit_indicator_animation = None
            self._release_speed_limit_indicator_animation_widgets()

        start_indicator_height = self._speed_limit_indicator.current_visible_height()
        end_indicator_height = SPEED_LIMIT_INDICATOR_EXPANDED_HEIGHT if is_visible else 0
        self._speed_limit_indicator_uses_window_resize = (
            self._should_resize_window_for_speed_limit_indicator()
        )
        self._speed_limit_indicator_start_height = start_indicator_height
        self._speed_limit_indicator_end_height = end_indicator_height
        self._speed_limit_indicator_start_window_height = self.height()
        self._speed_limit_indicator_end_window_height = (
            self._calculate_speed_limit_window_target_height(
                start_indicator_height=start_indicator_height,
                end_indicator_height=end_indicator_height,
            )
        )
        self._speed_limit_indicator_start_queue_height = max(1, self._queue_panel.height())
        self._speed_limit_indicator_end_queue_height = (
            self._calculate_speed_limit_queue_target_height(
                start_indicator_height=start_indicator_height,
                end_indicator_height=end_indicator_height,
            )
        )

        self._freeze_speed_limit_indicator_animation_widgets()
        self._apply_speed_limit_indicator_animation_frame(
            indicator_height=end_indicator_height,
            window_height=self._speed_limit_indicator_end_window_height,
            queue_height=self._speed_limit_indicator_end_queue_height,
        )

        if is_visible:
            self._speed_limit_indicator.set_expanded()
            self._is_speed_limit_window_extra_applied = True

            if self._speed_limit_indicator_uses_window_resize:
                self.setMinimumHeight(WINDOW_MINIMUM_HEIGHT + SPEED_LIMIT_INDICATOR_WINDOW_DELTA)

            self._release_speed_limit_indicator_animation_widgets()
            return

        self.setMinimumHeight(WINDOW_MINIMUM_HEIGHT)
        self._speed_limit_indicator.set_download_speed_limit(bytes_per_second=None)
        self._speed_limit_indicator.set_collapsed()
        self._is_speed_limit_window_extra_applied = False
        self._release_speed_limit_indicator_animation_widgets()

    def _animate_speed_limit_indicator_visibility(self, *, is_visible: bool) -> None:
        # stable adaptive speed limit indicator animation
        if self._speed_limit_indicator_animation is not None:
            self._speed_limit_indicator_animation.stop()
            self._speed_limit_indicator_animation = None
            self._release_speed_limit_indicator_animation_widgets()

        start_indicator_height = self._speed_limit_indicator.current_visible_height()
        end_indicator_height = SPEED_LIMIT_INDICATOR_EXPANDED_HEIGHT if is_visible else 0

        if start_indicator_height == end_indicator_height:
            self._apply_speed_limit_indicator_visibility_directly(is_visible=is_visible)
            return

        self._speed_limit_indicator_uses_window_resize = (
            self._should_resize_window_for_speed_limit_indicator()
        )
        self._speed_limit_indicator_animation_should_hide = not is_visible
        self._speed_limit_indicator_start_height = start_indicator_height
        self._speed_limit_indicator_end_height = end_indicator_height
        self._speed_limit_indicator_start_window_height = self.height()
        self._speed_limit_indicator_end_window_height = (
            self._calculate_speed_limit_window_target_height(
                start_indicator_height=start_indicator_height,
                end_indicator_height=end_indicator_height,
            )
        )
        self._speed_limit_indicator_start_queue_height = max(1, self._queue_panel.height())
        self._speed_limit_indicator_end_queue_height = (
            self._calculate_speed_limit_queue_target_height(
                start_indicator_height=start_indicator_height,
                end_indicator_height=end_indicator_height,
            )
        )

        self._freeze_speed_limit_indicator_animation_widgets()
        self.setMinimumHeight(WINDOW_MINIMUM_HEIGHT)
        self.setMaximumHeight(16_777_215)

        animation = QVariantAnimation(self)
        animation.setDuration(SPEED_LIMIT_INDICATOR_ANIMATION_DURATION_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.valueChanged.connect(self._handle_speed_limit_indicator_animation_value_changed)
        animation.finished.connect(self._handle_speed_limit_indicator_animation_finished)

        self._speed_limit_indicator_animation = animation
        animation.start()

    def _handle_speed_limit_indicator_animation_value_changed(self, value: object) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return

        progress = max(0.0, min(1.0, float(value)))
        indicator_height = round(
            self._speed_limit_indicator_start_height
            + (self._speed_limit_indicator_end_height - self._speed_limit_indicator_start_height)
            * progress
        )
        window_height = round(
            self._speed_limit_indicator_start_window_height
            + (
                self._speed_limit_indicator_end_window_height
                - self._speed_limit_indicator_start_window_height
            )
            * progress
        )
        queue_height = round(
            self._speed_limit_indicator_start_queue_height
            + (
                self._speed_limit_indicator_end_queue_height
                - self._speed_limit_indicator_start_queue_height
            )
            * progress
        )

        self._apply_speed_limit_indicator_animation_frame(
            indicator_height=indicator_height,
            window_height=window_height,
            queue_height=queue_height,
        )

    def _handle_speed_limit_indicator_animation_finished(self) -> None:
        final_window_height = max(
            WINDOW_MINIMUM_HEIGHT,
            self._speed_limit_indicator_end_window_height,
        )
        final_queue_height = max(1, self._speed_limit_indicator_end_queue_height)
        is_expanding = (
            self._speed_limit_indicator_end_height > self._speed_limit_indicator_start_height
        )

        self._apply_speed_limit_indicator_animation_frame(
            indicator_height=self._speed_limit_indicator_end_height,
            window_height=final_window_height,
            queue_height=final_queue_height,
        )

        if is_expanding:
            self._speed_limit_indicator.set_expanded()
            self._is_speed_limit_window_extra_applied = True

            if self._speed_limit_indicator_uses_window_resize:
                self.setMinimumHeight(WINDOW_MINIMUM_HEIGHT + SPEED_LIMIT_INDICATOR_WINDOW_DELTA)
            else:
                self.setMinimumHeight(WINDOW_MINIMUM_HEIGHT)
        else:
            self.setMinimumHeight(WINDOW_MINIMUM_HEIGHT)
            self._speed_limit_indicator.set_download_speed_limit(bytes_per_second=None)
            self._speed_limit_indicator.set_collapsed()
            self._is_speed_limit_window_extra_applied = False

        self._release_speed_limit_indicator_animation_widgets()
        self._speed_limit_indicator_animation = None

    def _apply_speed_limit_indicator_animation_frame(
        self,
        *,
        indicator_height: int,
        window_height: int,
        queue_height: int,
    ) -> None:
        if self._speed_limit_indicator_uses_window_resize:
            self._set_window_height_preserving_top(height=window_height)
        else:
            self._set_queue_panel_animation_height(height=queue_height)

        self._speed_limit_indicator.set_visible_height(height=indicator_height)

    def _calculate_speed_limit_window_target_height(
        self,
        *,
        start_indicator_height: int,
        end_indicator_height: int,
    ) -> int:
        if not self._speed_limit_indicator_uses_window_resize:
            return self._speed_limit_indicator_start_window_height

        indicator_height_delta = end_indicator_height - start_indicator_height

        return max(
            WINDOW_MINIMUM_HEIGHT,
            self._speed_limit_indicator_start_window_height + indicator_height_delta,
        )

    def _calculate_speed_limit_queue_target_height(
        self,
        *,
        start_indicator_height: int,
        end_indicator_height: int,
    ) -> int:
        if self._speed_limit_indicator_uses_window_resize:
            return max(1, self._speed_limit_indicator_start_queue_height)

        indicator_height_delta = end_indicator_height - start_indicator_height

        return max(1, self._speed_limit_indicator_start_queue_height - indicator_height_delta)

    def _resize_window_for_speed_limit_indicator_visibility(self, *, is_visible: bool) -> None:
        if self._is_speed_limit_window_extra_applied == is_visible:
            return

        self._apply_speed_limit_indicator_visibility_directly(is_visible=is_visible)

    def _resize_window_down_by_speed_limit_delta(self, *, delta_height: int) -> None:
        target_height = max(WINDOW_MINIMUM_HEIGHT, self.height() + delta_height)
        self._set_window_height_preserving_top(height=target_height)

    def _set_window_height_preserving_top(self, *, height: int) -> None:
        normalized_height = max(WINDOW_MINIMUM_HEIGHT, height)
        current_geometry = self.geometry()

        self.setMaximumHeight(16_777_215)
        self.setGeometry(
            current_geometry.left(),
            current_geometry.top(),
            current_geometry.width(),
            normalized_height,
        )

    def _set_queue_panel_animation_height(self, *, height: int) -> None:
        if self._speed_limit_indicator_queue_panel_limits is None:
            self._speed_limit_indicator_queue_panel_limits = (
                self._queue_panel.minimumHeight(),
                self._queue_panel.maximumHeight(),
            )

        normalized_height = max(1, height)
        self._queue_panel.setMinimumHeight(normalized_height)
        self._queue_panel.setMaximumHeight(normalized_height)

    def _restore_queue_panel_animation_height(self) -> None:
        queue_panel_limits = self._speed_limit_indicator_queue_panel_limits

        if queue_panel_limits is None:
            return

        minimum_height, maximum_height = queue_panel_limits
        self._queue_panel.setMinimumHeight(minimum_height)
        self._queue_panel.setMaximumHeight(maximum_height)
        self._queue_panel.updateGeometry()
        self._speed_limit_indicator_queue_panel_limits = None

    def _should_resize_window_for_speed_limit_indicator(self) -> bool:
        return not (self.isMaximized() or self.isFullScreen())

    def _freeze_speed_limit_indicator_animation_widgets(self) -> None:
        if self._speed_limit_indicator_frozen_widget_limits:
            return

        frozen_widgets = list[QWidget](
            (
                self._header,
                self._input_panel,
                self._settings_panel,
            )
        )

        if self._speed_limit_indicator_uses_window_resize:
            frozen_widgets.append(self._queue_panel)

        self._speed_limit_indicator_frozen_widget_limits = tuple(
            (widget, widget.minimumHeight(), widget.maximumHeight()) for widget in frozen_widgets
        )

        for widget in frozen_widgets:
            widget.setFixedHeight(widget.height())

    def _release_speed_limit_indicator_animation_widgets(self) -> None:
        self._restore_queue_panel_animation_height()

        for (
            widget,
            minimum_height,
            maximum_height,
        ) in self._speed_limit_indicator_frozen_widget_limits:
            widget.setMinimumHeight(minimum_height)
            widget.setMaximumHeight(maximum_height)
            widget.updateGeometry()

        self._speed_limit_indicator_frozen_widget_limits = ()

    def _handle_row_selection_mode_changed(self, is_active: bool) -> None:
        if is_active:
            self._footer_status_presenter.show_activity(
                message=ROW_SELECTION_MODE_STATUS_MESSAGE,
            )
            return

        self._footer_status_presenter.clear_activity(
            message=ROW_SELECTION_MODE_STATUS_MESSAGE,
        )

    def _sync_queue_controls_state(self) -> None:
        has_tasks = self._queue_table.has_tasks()
        has_selected_tasks = bool(self._queue_table.get_selected_task_ids())
        has_downloadable_tasks = bool(
            self._container.download_queue_service.list_downloadable_tasks()
        )
        has_active_download = self._download_controller.is_active
        has_active_tool_installation = self._tool_installation_controller.is_active
        has_active_ytdlp_runtime_operation = self._ytdlp_runtime_controller.is_active
        has_active_browser_cookies_export = self._browser_cookies_controller.is_active
        has_environment_operation = (
            has_active_tool_installation
            or has_active_ytdlp_runtime_operation
            or has_active_browser_cookies_export
        )
        has_blocking_operation = has_active_download or has_environment_operation

        self._input_panel.set_add_to_queue_available(
            is_available=not has_environment_operation,
        )
        self._settings_panel.choose_downloads_dir_button.setEnabled(not has_blocking_operation)
        self._environment_panel.prepare_system_button.setEnabled(not has_blocking_operation)
        self._environment_panel.update_tools_button.setEnabled(not has_blocking_operation)
        self._environment_panel.cookies_actions_button.setEnabled(not has_blocking_operation)
        self._environment_panel.delete_cookies_button.setEnabled(not has_blocking_operation)
        self._environment_panel.refresh_button.setEnabled(not has_blocking_operation)
        self._environment_panel.open_cookies_dir_button.setEnabled(not has_blocking_operation)
        self._environment_panel.open_downloads_dir_button.setEnabled(True)

        self._start_queue_button.setEnabled(
            not has_environment_operation and (has_active_download or has_downloadable_tasks)
        )
        self._remove_from_queue_button.setEnabled(has_selected_tasks and not has_blocking_operation)
        self._clear_queue_button.setEnabled(has_tasks and not has_blocking_operation)
        self._sync_start_queue_button_state()

    def _sync_start_queue_button_state(self) -> None:
        if self._download_controller.is_active:
            self._start_queue_button.setText("Отменить загрузку")
            self._start_queue_button.setObjectName("DangerButton")
        else:
            self._start_queue_button.setText("Скачать очередь")
            self._start_queue_button.setObjectName("SuccessButton")

        style = self._start_queue_button.style()

        if isinstance(style, QStyle):
            style.unpolish(self._start_queue_button)
            style.polish(self._start_queue_button)

    def _focus_url_input_later(self) -> None:
        QTimer.singleShot(0, self._input_panel.focus_url_input)


def calculate_history_adjusted_window_minimum_width(*, history_panel_width: int) -> int:
    safe_history_panel_width = max(0, history_panel_width)
    return WINDOW_MINIMUM_WIDTH + safe_history_panel_width


def is_same_filesystem_path(*, left_path: Path, right_path: Path) -> bool:
    try:
        return left_path.samefile(right_path)
    except OSError:
        return left_path.resolve() == right_path.resolve()
