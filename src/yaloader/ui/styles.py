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

QFrame#EnvironmentPanel {
    background-color: #12161D;
    border: 1px solid #252B35;
    border-radius: 14px;
}

QLabel#TitleLabel {
    font-size: 24pt;
    font-weight: 700;
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

QLabel#StatusChip {
    padding: 4px 10px;
    border-radius: 10px;
    background-color: #0D1117;
    border: 1px solid #30363D;
    color: #AEB8C4;
}

QLabel#StatusChip[state="ok"] {
    color: #A7F3D0;
    border-color: #1F6F4A;
    background-color: #0D1F18;
}

QLabel#StatusChip[state="warning"] {
    color: #FCD34D;
    border-color: #7C5E10;
    background-color: #211A0B;
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

QPushButton#SecondaryButton {
    background-color: #21262D;
    color: #C9D1D9;
    border: 1px solid #30363D;
}

QPushButton#SecondaryButton:hover {
    background-color: #30363D;
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

QPushButton#DangerGhostButton {
    background-color: transparent;
    color: #FCA5A5;
    border: 1px solid #553333;
}

QPushButton#DangerGhostButton:hover {
    background-color: #2A1518;
    color: #FECACA;
}

QPushButton:disabled {
    background-color: #2D333B;
    color: #7D8590;
    border-color: #30363D;
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
    selection-background-color: #1F6FEB;
    selection-color: #FFFFFF;
}

QTableWidget::item {
    padding: 8px;
    border: none;
}

QTableWidget::item:hover {
    background-color: #161B22;
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
"""
