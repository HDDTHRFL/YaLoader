from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from yaloader.config.app_info import APP_DISPLAY_NAME
from yaloader.domain.enums import OutputFormat, VideoQuality
from yaloader.services.app_container import AppContainer


class MainWindow(QMainWindow):
    def __init__(self, container: AppContainer) -> None:
        super().__init__()

        self._container = container
        self._url_input = QLineEdit(self)
        self._quality_combo_box = QComboBox(self)
        self._format_combo_box = QComboBox(self)
        self._download_button = QPushButton("Добавить в очередь", self)
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
            self._quality_combo_box.addItem(quality.value)

        for output_format in OutputFormat:
            self._format_combo_box.addItem(output_format.value)

        self._status_label.setObjectName("StatusLabel")
        self._status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    def _connect_signals(self) -> None:
        self._download_button.clicked.connect(self._handle_add_to_queue_clicked)

    def _build_central_widget(self) -> QWidget:
        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(28, 24, 28, 24)
        root_layout.setSpacing(18)

        root_layout.addWidget(self._build_header())
        root_layout.addWidget(self._build_input_panel())
        root_layout.addWidget(self._build_queue_placeholder(), stretch=1)
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

    def _build_queue_placeholder(self) -> QFrame:
        panel = QFrame(self)
        panel.setObjectName("PanelFrame")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title_label = QLabel("Очередь загрузок", panel)
        title_label.setObjectName("SectionTitleLabel")

        placeholder_label = QLabel(
            "Очередь будет добавлена следующим шагом. Сейчас проверяем базовый запуск GUI.",
            panel,
        )
        placeholder_label.setObjectName("MutedLabel")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title_label)
        layout.addItem(
            QSpacerItem(
                20,
                20,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
        )
        layout.addWidget(placeholder_label)
        layout.addItem(
            QSpacerItem(
                20,
                20,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
        )

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
            self._status_label.setText("Сначала вставь ссылку")
            return

        self._status_label.setText("Следующим шагом подключим создание задачи загрузки")
