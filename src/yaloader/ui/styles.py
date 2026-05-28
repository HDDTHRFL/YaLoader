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

QLabel#FieldLabel {
    font-size: 10pt;
    font-weight: 600;
    color: #C9D1D9;
}

QLabel#MutedLabel {
    color: #8B949E;
}

QLabel#StatusLabel {
    color: #9AA4B2;
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
    background-color: #B42318;
    color: #FFFFFF;
}

QPushButton#DangerButton:hover {
    background-color: #D92D20;
}

QPushButton#DangerButton:pressed {
    background-color: #912018;
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

QMenu {
    background-color: #161B22;
    color: #F0F3F6;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #1F6FEB;
    color: #FFFFFF;
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

QFrame#HistoryPanel {
    background-color: #13161D;
    border-left: 1px solid #272C36;
}

QScrollArea#HistoryScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea#HistoryScrollArea QWidget {
    background-color: transparent;
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

QLabel#HistoryUrlLabel {
    color: #E8EAED;
    font-size: 9pt;
}

QLabel#HistoryPathLabel {
    color: #8B949E;
    font-size: 8pt;
}

QLabel#HistoryErrorLabel {
    color: #FCA5A5;
    font-size: 8pt;
}
"""
