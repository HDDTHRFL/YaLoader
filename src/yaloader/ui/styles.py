from __future__ import annotations

APP_STYLE_SHEET = """
QMainWindow {
    background-color: #101216;
}

QWidget {
    color: #E8EAED;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QFrame#PanelFrame {
    background-color: #171A21;
    border: 1px solid #272C36;
    border-radius: 14px;
}

QFrame#SpeedLimitIndicatorPanel {
    background-color: transparent;
    border: none;
}

QFrame#EnvironmentPanelFrame {
    background-color: transparent;
    border: none;
}

QLabel#TitleLabel {
    font-family: "Death Stars", "Segoe UI Black", "Arial Black";
    font-size: 40pt;
    font-weight: 400;
    color: #FFFFFF;
}

QLabel#SubtitleLabel {
    font-size: 11pt;
    color: #9AA4B2;
}

QLabel#SectionTitleLabel {
    font-size: 13pt;
    font-weight: 600;
    color: #F3F5F7;
}

QLabel#SmallSectionTitleLabel {
    font-size: 10pt;
    font-weight: 600;
    color: #C9D1D9;
}

QLabel#EnvironmentSectionTitleLabel {
    font-size: 13pt;
    font-weight: 700;
    color: #F3F5F7;
}

QLabel#FieldLabel {
    font-size: 10pt;
    font-weight: 600;
    color: #C9D1D9;
}

QLabel#MutedLabel {
    color: #8B949E;
}

QLabel#SpeedLimitLabel {
    color: #FCD34D;
    font-size: 9pt;
    font-weight: 600;
}

QLabel#StatusLabel {
    color: #9AA4B2;
}

QLabel#StatusLabel[statusKind="activity"] {
    color: #58A6FF;
    font-weight: 600;
}

QLabel#QueueEmptyHintLabel {
    color: #6E7681;
    background-color: transparent;
    font-size: 11pt;
    font-weight: 500;
}

QFrame#StatusChipFrame {
    border-radius: 10px;
    background-color: #0D1117;
    border: 1px solid #30363D;
}

QFrame#StatusChipFrame[state="ok"] {
    border-color: #1F6F4A;
    background-color: #0D1F18;
}

QFrame#StatusChipFrame[state="warning"] {
    border-color: #7C5E10;
    background-color: #211A0B;
}

QFrame#StatusChipFrame[refreshing="true"] {
    border-color: #2F81F7;
    background-color: #11233A;
}

QLabel#StatusDot {
    min-width: 10px;
    max-width: 10px;
    margin-top: -2px;
    font-size: 8pt;
    color: #8B949E;
}

QLabel#StatusDot[state="ok"] {
    color: #34D399;
}

QLabel#StatusDot[state="warning"] {
    color: #FCD34D;
}

QLabel#StatusChipText {
    color: #AEB8C4;
}

QFrame#StatusChipFrame[state="ok"] QLabel#StatusChipText {
    color: #A7F3D0;
}

QFrame#StatusChipFrame[state="warning"] QLabel#StatusChipText {
    color: #FCD34D;
}


QLabel#StatusChipText[state="ok"] {
    color: #A7F3D0;
}

QLabel#StatusChipText[state="warning"] {
    color: #FCD34D;
}

QLineEdit {
    min-height: 36px;
    padding: 0 12px;
    background-color: #0D1117;
    color: #F0F3F6;
    border: 1px solid #30363D;
    border-radius: 10px;
    selection-background-color: #2F81F7;
}

QLineEdit:focus {
    border: 1px solid #2F81F7;
}

QComboBox {
    min-height: 36px;
    min-width: 92px;
    padding: 0 24px 0 10px;
    background-color: #0D1117;
    color: #F0F3F6;
    border: 1px solid #30363D;
    border-radius: 10px;
}

QComboBox:hover {
    border: 1px solid #3D444D;
}

QComboBox:focus {
    border: 1px solid #2F81F7;
}

QComboBox::drop-down {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 24px;
    background-color: transparent;
    border: none;
}

QComboBox::down-arrow {
    width: 8px;
    height: 8px;
}

QComboBox QAbstractItemView {
    background-color: #161B22;
    color: #F0F3F6;
    border: 1px solid #30363D;
    selection-background-color: #2F81F7;
    selection-color: #FFFFFF;
    outline: 0;
}

QPushButton {
    min-height: 36px;
    padding: 0 18px;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    outline: 0;
}

QPushButton:focus {
    outline: 0;
}

QPushButton#PrimaryButton,
QPushButton {
    background-color: #238636;
    color: #FFFFFF;
}

QPushButton#PrimaryButton:hover,
QPushButton:hover {
    background-color: #2EA043;
}

QPushButton#PrimaryButton:pressed,
QPushButton:pressed {
    background-color: #1F6F2A;
}

QPushButton#DangerButton {
    background-color: #2A1518;
    color: #FECACA;
    border: 1px solid #553333;
}

QPushButton#DangerButton:hover {
    background-color: #3A1518;
    color: #FFFFFF;
    border-color: #D92D20;
}

QPushButton#DangerButton:pressed {
    background-color: #4A1116;
    color: #FFFFFF;
    border-color: #F97066;
}

QPushButton#SecondaryButton {
    background-color: #21262D;
    color: #C9D1D9;
    border: 1px solid #30363D;
}

QPushButton#SecondaryButton:hover {
    background-color: #30363D;
}

QPushButton#SecondaryButton:pressed {
    background-color: #151A21;
    border-color: #2F81F7;
    color: #FFFFFF;
}

QPushButton#GhostButton {
    min-height: 28px;
    padding: 0 12px;
    background-color: transparent;
    color: #8B949E;
    border: 1px solid #30363D;
    border-radius: 8px;
    font-weight: 500;
}

QPushButton#GhostButton:hover {
    background-color: #1B2028;
    color: #C9D1D9;
}

QPushButton#GhostButton:pressed {
    background-color: #0D1117;
    border-color: #2F81F7;
    color: #FFFFFF;
}

QPushButton#TinyGhostButton {
    min-height: 24px;
    padding: 0 10px;
    background-color: transparent;
    color: #7D8590;
    border: 1px solid #30363D;
    border-radius: 7px;
    font-weight: 500;
    font-size: 9pt;
}

QPushButton#TinyGhostButton:hover {
    background-color: #1B2028;
    color: #C9D1D9;
}

QPushButton#TinyGhostButton:pressed {
    background-color: #0D1117;
    border-color: #2F81F7;
    color: #FFFFFF;
}

QPushButton#IconButton {
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
    padding: 0 0 0px 0;
    background-color: transparent;
    color: #8B949E;
    border: 1px solid #30363D;
    border-radius: 10px;
    font-family: "Segoe UI Symbol", "Segoe UI Emoji", "Segoe UI";
    font-size: 14pt;
    font-weight: 500;
}

QPushButton#IconButton:hover {
    background-color: #1B2028;
    color: #FFFFFF;
    border-color: #3D444D;
}

QPushButton#IconButton:pressed {
    background-color: #0D1117;
    color: #C9D1D9;
    border-color: #2F81F7;
}

QPushButton#TinyDangerButton {
    min-height: 24px;
    padding: 0 10px;
    background-color: transparent;
    color: #FCA5A5;
    border: 1px solid #553333;
    border-radius: 7px;
    font-weight: 500;
    font-size: 9pt;
}

QPushButton#TinyDangerButton:hover {
    background-color: #2A1518;
    color: #FECACA;
}

QPushButton#TinyDangerButton:pressed {
    background-color: #3A1518;
    border-color: #D92D20;
    color: #FFFFFF;
}

QPushButton#DangerGhostButton {
    background-color: transparent;
    color: #FCA5A5;
    border: 1px solid #553333;
}

QPushButton#DangerGhostButton:hover {
    background-color: #2A1518;
    color: #FECACA;
}

QPushButton#DangerGhostButton:pressed {
    background-color: #3A1518;
    border-color: #D92D20;
    color: #FFFFFF;
}

QPushButton#MenuDangerButton {
    min-height: 32px;
    padding: 0 24px;
    background-color: transparent;
    color: #FCA5A5;
    border: none;
    border-radius: 6px;
    font-weight: 500;
    text-align: left;
}

QPushButton#MenuDangerButton:hover {
    background-color: #3A1518;
    color: #FECACA;
}

QPushButton:disabled,
QPushButton#PrimaryButton:disabled,
QPushButton#SecondaryButton:disabled,
QPushButton#DangerButton:disabled,
QPushButton#GhostButton:disabled,
QPushButton#TinyGhostButton:disabled,
QPushButton#TinyDangerButton:disabled,
QPushButton#DangerGhostButton:disabled,
QPushButton#MenuDangerButton:disabled {
    background-color: #1A1F27;
    color: #5F6875;
    border: 1px solid #252B35;
}

QPushButton#PrimaryButton:disabled:hover,
QPushButton#SecondaryButton:disabled:hover,
QPushButton#DangerButton:disabled:hover,
QPushButton#GhostButton:disabled:hover,
QPushButton#TinyGhostButton:disabled:hover,
QPushButton#TinyDangerButton:disabled:hover,
QPushButton#DangerGhostButton:disabled:hover,
QPushButton#MenuDangerButton:disabled:hover {
    background-color: #1A1F27;
    color: #5F6875;
    border: 1px solid #252B35;
}

QProgressBar {
    min-height: 18px;
    background-color: #0D1117;
    color: #F0F3F6;
    border: 1px solid #30363D;
    border-radius: 8px;
    text-align: center;
    font-size: 9pt;
}

QProgressBar::chunk {
    background-color: #238636;
    border-radius: 7px;
}

QTableWidget {
    background-color: #0D1117;
    alternate-background-color: #111722;
    color: #F0F3F6;
    border: 1px solid #30363D;
    border-radius: 10px;
    gridline-color: #21262D;
    selection-background-color: #1F3A5F;
    selection-color: #FFFFFF;
}

QTableWidget::item {
    padding: 8px;
    border: none;
}

QTableWidget::item:hover {
    background-color: #161B22;
}

QTableWidget::item:selected,
QTableWidget::item:selected:active,
QTableWidget::item:selected:!active {
    background-color: #1F3A5F;
    color: #FFFFFF;
}

QTableWidget::item:selected:hover,
QTableWidget::item:selected:active:hover,
QTableWidget::item:selected:!active:hover {
    background-color: #284A73;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #161B22;
    color: #C9D1D9;
    padding: 8px;
    border: none;
    border-right: 1px solid #30363D;
    border-bottom: 1px solid #30363D;
    font-weight: 600;
}

QTableCornerButton::section {
    background-color: #161B22;
    border: none;
}

QScrollBar:vertical {
    width: 10px;
    background-color: transparent;
    margin: 2px 2px 2px 2px;
}

QScrollBar::handle:vertical {
    min-height: 28px;
    background-color: #30363D;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3D444D;
}

QScrollBar::handle:vertical:pressed {
    background-color: #4B5563;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    background-color: transparent;
    border: none;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background-color: transparent;
}

QScrollBar:horizontal {
    height: 10px;
    background-color: transparent;
    margin: 2px 2px 2px 2px;
}

QScrollBar::handle:horizontal {
    min-width: 28px;
    background-color: #30363D;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #3D444D;
}

QScrollBar::handle:horizontal:pressed {
    background-color: #4B5563;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
    background-color: transparent;
    border: none;
}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background-color: transparent;
}




QScrollBar#OverlayScrollBar:vertical {
    background-color: transparent;
    margin: 0;
    border: none;
}

QScrollBar#OverlayScrollBar::handle:vertical {
    background-color: transparent;
    border: none;
}

QScrollBar#OverlayScrollBar::handle:vertical:hover {
    background-color: transparent;
    border: none;
}

QScrollBar#OverlayScrollBar::handle:vertical:pressed {
    background-color: transparent;
    border: none;
}

QScrollBar#OverlayScrollBar::add-line:vertical,
QScrollBar#OverlayScrollBar::sub-line:vertical {
    height: 0;
    background-color: transparent;
    border: none;
}

QScrollBar#OverlayScrollBar::add-page:vertical,
QScrollBar#OverlayScrollBar::sub-page:vertical {
    background-color: transparent;
}

QDialog#SpeedSettingsDialog {
    background-color: #161B22;
    border: 1px solid #30363D;
    border-radius: 8px;
}

QLabel#SpeedSettingsPopupTitle {
    color: #F3F5F7;
    font-size: 10pt;
    font-weight: 700;
}

QSpinBox#SpeedLimitSpinBox {
    min-height: 34px;
    min-width: 150px;
    padding: 0 10px;
    background-color: #0D1117;
    color: #F0F3F6;
    border: 1px solid #30363D;
    border-radius: 8px;
    selection-background-color: #2F81F7;
}

QSpinBox#SpeedLimitSpinBox:hover {
    border-color: #3D444D;
}

QSpinBox#SpeedLimitSpinBox:focus {
    border-color: #2F81F7;
}

QSpinBox#SpeedLimitSpinBox::up-button,
QSpinBox#SpeedLimitSpinBox::down-button {
    width: 0;
    border: none;
    background-color: transparent;
}



QPushButton#SpeedResetButton {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
    background-color: transparent;
    color: #8B949E;
    border: none;
    border-radius: 0;
    font-family: "Segoe UI Symbol", "Segoe UI Emoji", "Segoe UI";
    font-size: 14pt;
    font-weight: 700;
}

QPushButton#SpeedResetButton:hover {
    background-color: transparent;
    color: #FFFFFF;
    border: none;
}

QPushButton#SpeedResetButton:pressed {
    background-color: transparent;
    color: #8B949E;
    border: none;
}






QSlider#SpeedLimitSlider {
    min-height: 28px;
}

QSlider#SpeedLimitSlider::groove:horizontal {
    height: 5px;
    background-color: #30363D;
    border-radius: 3px;
}

QSlider#SpeedLimitSlider[pressed="true"]::groove:horizontal {
    height: 7px;
    border-radius: 4px;
}

QSlider#SpeedLimitSlider::sub-page:horizontal {
    height: 5px;
    background-color: #C9D1D9;
    border-radius: 3px;
}

QSlider#SpeedLimitSlider[hovered="true"]::sub-page:horizontal {
    background-color: #F0F3F6;
}

QSlider#SpeedLimitSlider[pressed="true"]::sub-page:horizontal {
    height: 7px;
    background-color: #FCD34D;
    border-radius: 4px;
}

QSlider#SpeedLimitSlider::handle:horizontal {
    width: 14px;
    height: 14px;
    margin: -5px 0;
    background-color: #C9D1D9;
    border: 2px solid #C9D1D9;
    border-radius: 7px;
}

QSlider#SpeedLimitSlider[hovered="true"]::handle:horizontal {
    background-color: #F0F3F6;
    border-color: #F0F3F6;
}

QSlider#SpeedLimitSlider[pressed="true"]::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -6px 0;
    background-color: #FCD34D;
    border: 2px solid #FFE58A;
    border-radius: 8px;
}

QSpinBox#SpeedLimitSpinBox[sliderPressed="true"] {
    color: #FCD34D;
}

QMenu {
    background-color: #161B22;
    color: #F0F3F6;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 6px;
}

QFrame#HistoryDrawerToggleStrip {
    background-color: transparent;
    border: none;
}

QPushButton#DrawerToggleButton {
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    padding: 0;
    background-color: transparent;
    color: #C9D1D9;
    border: none;
    border-radius: 0;
    font-size: 22pt;
    font-weight: 700;
}

QPushButton#DrawerToggleButton:hover {
    background-color: transparent;
    color: #FFFFFF;
    border: none;
}

QPushButton#DrawerToggleButton:pressed {
    background-color: transparent;
    color: #8B949E;
    border: none;
}

QPushButton#SettingsToolButton {
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
    padding: 0;
    background-color: transparent;
    color: #C9D1D9;
    border: none;
    border-radius: 0;
    font-family: "Segoe UI Symbol", "Segoe UI Emoji", "Segoe UI";
    font-size: 21pt;
    font-weight: 700;
}

QPushButton#SettingsToolButton:hover {
    background-color: transparent;
    color: #FFFFFF;
    border: none;
}

QPushButton#SettingsToolButton:pressed {
    background-color: transparent;
    color: #8B949E;
    border: none;
}

QFrame#HistoryPanel {
    background-color: #13161D;
    border-left: 1px solid #272C36;
}

QWidget#HistoryPanelContent,
QWidget#HistoryRecordsContainer,
QWidget#HistoryScrollAreaViewport {
    background-color: #13161D;
}

QScrollArea#HistoryScrollArea {
    background-color: #13161D;
    border: none;
}

QScrollArea#HistoryScrollArea QWidget {
    background-color: #13161D;
}

QFrame#HistoryCard {
    background-color: #0D1117;
    border: 1px solid #30363D;
    border-radius: 10px;
}

QFrame#HistoryCard[state="completed"] {
    border-color: #1F6F4A;
}

QFrame#HistoryCard[state="failed"] {
    border-color: #553333;
}

QFrame#HistoryCard[state="canceled"] {
    border-color: #5C4A1E;
}

QLabel#HistoryStatusLabel {
    font-size: 9pt;
    font-weight: 700;
}

QLabel#HistoryStatusLabel[state="completed"] {
    color: #A7F3D0;
}

QLabel#HistoryStatusLabel[state="failed"] {
    color: #FCA5A5;
}

QLabel#HistoryStatusLabel[state="canceled"] {
    color: #FCD34D;
}

QLabel#HistoryTimeLabel {
    color: #7D8590;
    font-size: 9pt;
}

QLabel#HistoryTitleLabel {
    color: #F0F3F6;
    font-size: 10pt;
    font-weight: 600;
}

QLabel#HistoryUrlLabel {
    color: #C9D1D9;
    font-size: 9pt;
}

QLabel#HistoryUrlLabel:hover {
    color: #FFFFFF;
    text-decoration: underline;
}

QLabel#HistoryPathLabel {
    color: #8B949E;
    font-size: 8pt;
}

QLabel#HistoryPathLabel:hover {
    color: #C9D1D9;
    text-decoration: underline;
}

QLabel#HistoryErrorLabel {
    color: #FCA5A5;
    font-size: 8pt;
}

QPushButton#RefreshIconButton {
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
    padding: 0;
    background-color: transparent;
    color: #8B949E;
    border: none;
    border-radius: 13px;
    font-family: "Segoe UI Symbol", "Segoe UI Emoji", "Segoe UI";
    font-size: 15pt;
    font-weight: 700;
}

QPushButton#RefreshIconButton:hover {
    background-color: transparent;
    color: #FFFFFF;
    border: none;
}

QPushButton#RefreshIconButton:pressed {
    background-color: transparent;
    color: #58A6FF;
    border: none;
}

QPushButton#RefreshIconButton:disabled,
QPushButton#RefreshIconButton:disabled:hover {
    background-color: transparent;
    color: #4B5563;
    border: none;
}

QProgressBar#ToolInstallationProgressBar {
    min-height: 12px;
    max-height: 12px;
    background-color: #0D1117;
    color: #9AA4B2;
    border: 1px solid #30363D;
    border-radius: 6px;
    text-align: center;
    font-size: 8pt;
    font-weight: 600;
}

QProgressBar#ToolInstallationProgressBar::chunk {
    background-color: #2F81F7;
    border-radius: 5px;
}



QLabel#DownloadsDirClickableLabel {
    color: #8B949E;
}

QLabel#DownloadsDirClickableLabel:hover {
    color: #58A6FF;
}



QMenu#CookiesActionsMenu {
    background-color: #171A21;
    color: #E8EAED;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 6px;
}

QMenu#CookiesActionsMenu::item {
    padding: 7px 22px 7px 10px;
    border-radius: 6px;
}

QMenu#CookiesActionsMenu::item:selected {
    background-color: #1F6FEB;
    color: #FFFFFF;
}


/* YaLoader environment toolbar fine tuning start */
QPushButton#RefreshIconButton {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0 0 2px 0; /* padding-bottom поднимает символ, padding-top опускает */
    background-color: transparent;
    color: #8B949E;
    border: none;
    border-radius: 14px;
    font-family: "Segoe UI Symbol", "Segoe UI Emoji", "Segoe UI";
    font-size: 13pt;
    font-weight: 700;
}

QPushButton#RefreshIconButton:hover {
    background-color: transparent;
    color: #FFFFFF;
    border: none;
}

QPushButton#RefreshIconButton:pressed {
    background-color: transparent;
    color: #58A6FF;
    border: none;
}

QPushButton#RefreshIconButton:disabled,
QPushButton#RefreshIconButton:disabled:hover {
    background-color: transparent;
    color: #4B5563;
    border: none;
}

QMenu#CookiesActionsMenu {
    background-color: #171A21;
    color: #C9D1D9;
    border: 1px solid #30363D;
    border-radius: 7px;
    padding: 3px;
    font-size: 9pt;
}

QMenu#CookiesActionsMenu::item {
    min-height: 18px;
    padding: 4px 14px 4px 10px;
    border-radius: 5px;
    background-color: transparent;
}

QMenu#CookiesActionsMenu::item:selected {
    padding: 4px 12px 4px 12px;
    background-color: #1B2028;
    color: #FFFFFF;
}

QMenu#CookiesActionsMenu::item:pressed {
    background-color: #0D1117;
    color: #58A6FF;
}
/* YaLoader environment toolbar fine tuning end */

/* YaLoader final environment polish start */
QLabel#DownloadsDirClickableLabel:hover {
    color: #FFFFFF;
}

QPushButton#RefreshIconButton {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
    background-color: transparent;
    color: #8B949E;
    border: none;
    border-radius: 0;
    font-family: "Segoe UI Symbol", "Segoe UI Emoji", "Segoe UI";
    font-size: 15pt;
    font-weight: 700;
}

QPushButton#RefreshIconButton:hover {
    background-color: transparent;
    color: #FFFFFF;
    border: none;
}

QPushButton#RefreshIconButton:pressed {
    background-color: transparent;
    color: #8B949E;
    border: none;
}

QPushButton#RefreshIconButton:disabled,
QPushButton#RefreshIconButton:disabled:hover {
    background-color: transparent;
    color: #4B5563;
    border: none;
}
/* YaLoader final environment polish end */

/* YaLoader success action buttons start */
QPushButton#SuccessButton {
    min-height: 36px;
    padding: 0 18px;
    background-color: #1F6F4A;
    color: #D1FAE5;
    border: 1px solid #238636;
    border-radius: 10px;
    font-weight: 700;
}

QPushButton#SuccessButton:hover {
    background-color: #238636;
    color: #FFFFFF;
    border-color: #2EA043;
}

QPushButton#SuccessButton:pressed {
    background-color: #1A5A3C;
    color: #FFFFFF;
    border-color: #3FB950;
}

QPushButton#SuccessButton:focus {
    border-color: #3FB950;
}

QPushButton#SuccessButton:disabled,
QPushButton#SuccessButton:disabled:hover {
    background-color: #1A1F27;
    color: #5F6875;
    border: 1px solid #252B35;
}
/* YaLoader success action buttons end */

"""
