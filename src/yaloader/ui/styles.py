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
    padding: 0 10px;
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
    background-color: #238636;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2EA043;
}

QPushButton:pressed {
    background-color: #1F6F2A;
}
"""
