from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from yaloader.application.dto.environment_status import EnvironmentItemStatus, EnvironmentStatus

REFRESH_FEEDBACK_DURATION_MS = 160
REFRESH_ICON_BUTTON_SIZE_PX = 28


class StatusChip(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._marker_label = QLabel("●", self)
        self._text_label = QLabel(self)

        self._configure_widgets()
        self._build_layout()

    def set_status(self, status: EnvironmentItemStatus) -> None:
        state = "ok" if status.is_ok else "warning"

        self.setProperty("state", state)
        self.setProperty("refreshing", "false")
        self._marker_label.setProperty("state", state)
        self._text_label.setProperty("state", state)
        self._text_label.setText(f"{status.title}: {status.message}")

        tooltip = str(status.path) if status.path is not None else status.message
        self.setToolTip(tooltip)
        self._text_label.setToolTip(tooltip)

        self._refresh_style(self)
        self._refresh_style(self._marker_label)
        self._refresh_style(self._text_label)

    def play_refresh_feedback(self) -> None:
        self.setProperty("refreshing", "true")
        self._refresh_style(self)

        QTimer.singleShot(REFRESH_FEEDBACK_DURATION_MS, self._clear_refresh_feedback)

    def _clear_refresh_feedback(self) -> None:
        self.setProperty("refreshing", "false")
        self._refresh_style(self)

    def _configure_widgets(self) -> None:
        self.setObjectName("StatusChipFrame")
        self.setProperty("refreshing", "false")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        self._marker_label.setObjectName("StatusDot")
        self._marker_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._marker_label.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        self._text_label.setObjectName("StatusChipText")
        self._text_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._text_label.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    def _build_layout(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(5, 2, 10, 7)
        layout.setHorizontalSpacing(3)
        layout.setVerticalSpacing(0)

        layout.addWidget(
            self._marker_label,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )
        layout.addWidget(self._text_label, 0, 1)
        layout.setColumnStretch(1, 1)

    def _refresh_style(self, widget: QWidget) -> None:
        style = widget.style()

        if isinstance(style, QStyle):
            style.unpolish(widget)
            style.polish(widget)


class EnvironmentPanel(QFrame):
    refresh_button: QPushButton
    prepare_system_button: QPushButton
    update_tools_button: QPushButton

    cookies_actions_button: QPushButton
    import_cookies_action: QAction
    export_firefox_cookies_action: QAction
    export_opera_cookies_action: QAction
    export_chrome_cookies_action: QAction

    open_cookies_dir_button: QPushButton
    delete_cookies_button: QPushButton
    open_downloads_dir_button: QPushButton

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.refresh_button = QPushButton("⟲", self)
        self.prepare_system_button = QPushButton("Подготовить систему", self)
        self.update_tools_button = QPushButton("Обновить инструменты", self)

        self.cookies_actions_button = QPushButton("Добавить cookies.txt", self)
        self.import_cookies_action = QAction("Импортировать файл...", self)
        self.export_firefox_cookies_action = QAction("Создать из Firefox", self)
        self.export_opera_cookies_action = QAction("Создать из Opera", self)
        self.export_chrome_cookies_action = QAction("Создать из Chrome", self)
        self._cookies_actions_menu = QMenu(self.cookies_actions_button)

        self.open_cookies_dir_button = QPushButton("Открыть cookies", self)
        self.delete_cookies_button = QPushButton("Удалить cookies.txt", self)
        self.open_downloads_dir_button = QPushButton("Открыть загрузки", self)

        self._ffmpeg_status_chip = StatusChip(self)
        self._deno_status_chip = StatusChip(self)
        self._ytdlp_status_chip = StatusChip(self)
        self._cookies_status_chip = StatusChip(self)
        self._downloads_dir_status_chip = StatusChip(self)

        self._configure_widgets()
        self._build_layout()

    def set_status(self, status: EnvironmentStatus) -> None:
        self._ffmpeg_status_chip.set_status(status.ffmpeg)
        self._deno_status_chip.set_status(status.deno)
        self._ytdlp_status_chip.set_status(status.ytdlp)
        self._cookies_status_chip.set_status(status.cookies)
        self._downloads_dir_status_chip.set_status(status.downloads_dir)

    def play_refresh_feedback(self) -> None:
        for chip in self._status_chips:
            chip.play_refresh_feedback()

    def _configure_widgets(self) -> None:
        self.setObjectName("EnvironmentPanelFrame")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        self.refresh_button.setObjectName("RefreshIconButton")
        self.refresh_button.setFixedSize(
            REFRESH_ICON_BUTTON_SIZE_PX,
            REFRESH_ICON_BUTTON_SIZE_PX,
        )
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prepare_system_button.setObjectName("GhostButton")
        self.update_tools_button.setObjectName("GhostButton")

        self.cookies_actions_button.setObjectName("TinyGhostButton")
        self.cookies_actions_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cookies_actions_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cookies_actions_menu.setObjectName("CookiesActionsMenu")
        self._cookies_actions_menu.addAction(self.export_firefox_cookies_action)
        self._cookies_actions_menu.addAction(self.export_opera_cookies_action)
        self._cookies_actions_menu.addAction(self.export_chrome_cookies_action)
        self._cookies_actions_menu.addAction(self.import_cookies_action)
        self.cookies_actions_button.setMenu(self._cookies_actions_menu)

        self.open_cookies_dir_button.setObjectName("TinyGhostButton")
        self.open_downloads_dir_button.setObjectName("TinyGhostButton")
        self.delete_cookies_button.setObjectName("TinyDangerButton")

        self.refresh_button.setToolTip("Повторно проверить состояние системы")
        self.prepare_system_button.setToolTip("Скачать и подключить FFmpeg и Deno в папку YaLoader")
        self.update_tools_button.setToolTip(
            "Принудительно скачать свежие FFmpeg и Deno в папку YaLoader"
        )
        self.cookies_actions_button.setToolTip(
            "Импортировать cookies.txt или создать его из Firefox"
        )
        self.open_cookies_dir_button.setToolTip("Открыть папку с cookies.txt")
        self.delete_cookies_button.setToolTip("Безвозвратно удалить cookies.txt")
        self.open_downloads_dir_button.setToolTip("Открыть папку загрузок")

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 12, 18, 12)
        root_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title_label = QLabel("Состояние системы", self)
        title_label.setObjectName("EnvironmentSectionTitleLabel")
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        title_label.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        header_layout.addWidget(
            title_label,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        header_layout.addWidget(
            self.refresh_button,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        header_layout.addStretch(1)
        header_layout.addWidget(
            self.prepare_system_button,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        header_layout.addWidget(
            self.update_tools_button,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )

        chips_layout = QHBoxLayout()
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(8)

        for chip in self._status_chips:
            chips_layout.addWidget(chip)

        chips_layout.addStretch(1)

        actions_layout = QGridLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setHorizontalSpacing(8)
        actions_layout.setVerticalSpacing(6)

        actions_layout.addWidget(self.cookies_actions_button, 0, 0)
        actions_layout.addWidget(self.open_cookies_dir_button, 0, 1)
        actions_layout.addWidget(self.open_downloads_dir_button, 0, 2)
        actions_layout.addWidget(self.delete_cookies_button, 1, 0)
        actions_layout.setColumnStretch(3, 1)

        root_layout.addLayout(header_layout)
        root_layout.addLayout(chips_layout)
        root_layout.addLayout(actions_layout)

    @property
    def _status_chips(self) -> tuple[StatusChip, ...]:
        return (
            self._ffmpeg_status_chip,
            self._deno_status_chip,
            self._ytdlp_status_chip,
            self._cookies_status_chip,
            self._downloads_dir_status_chip,
        )
