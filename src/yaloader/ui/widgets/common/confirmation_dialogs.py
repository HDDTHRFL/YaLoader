from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QPushButton, QWidget

CONFIRMATION_DIALOG_STYLE_SHEET = """
QMessageBox {
    background-color: #171A21;
}

QMessageBox QLabel {
    color: #E8EAED;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QMessageBox QPushButton {
    min-height: 34px;
    padding: 0 18px;
    border: 1px solid transparent;
    border-radius: 9px;
    font-weight: 600;
}

QMessageBox QPushButton#DialogDangerButton {
    background-color: #2A1518;
    color: #FECACA;
    border-color: #553333;
}

QMessageBox QPushButton#DialogDangerButton:hover {
    background-color: #3A1518;
    color: #FFFFFF;
    border-color: #D92D20;
}

QMessageBox QPushButton#DialogDangerButton:pressed {
    background-color: #4A1116;
    color: #FFFFFF;
    border-color: #F97066;
}

QMessageBox QPushButton#DialogDangerButton:focus {
    border-color: #D92D20;
}

QMessageBox QPushButton#DialogSecondaryButton {
    background-color: #21262D;
    color: #C9D1D9;
    border-color: #30363D;
}

QMessageBox QPushButton#DialogSecondaryButton:hover {
    background-color: #30363D;
    color: #FFFFFF;
    border-color: #3D444D;
}

QMessageBox QPushButton#DialogSecondaryButton:pressed {
    background-color: #151A21;
    border-color: #2F81F7;
    color: #FFFFFF;
}

QMessageBox QPushButton#DialogSecondaryButton:focus {
    border-color: #2F81F7;
}
"""


def confirm_dangerous_action(
    *,
    parent: QWidget,
    title: str,
    text: str,
    informative_text: str,
    confirm_button_text: str,
) -> bool:
    message_box = QMessageBox(parent)
    message_box.setWindowTitle(title)
    message_box.setIcon(QMessageBox.Icon.Warning)
    message_box.setText(text)
    message_box.setInformativeText(informative_text)
    message_box.setTextFormat(Qt.TextFormat.PlainText)
    message_box.setModal(True)
    message_box.setStyleSheet(CONFIRMATION_DIALOG_STYLE_SHEET)

    confirm_button = QPushButton(confirm_button_text, message_box)
    confirm_button.setObjectName("DialogDangerButton")
    confirm_button.setCursor(Qt.CursorShape.PointingHandCursor)

    cancel_button = QPushButton("Отмена", message_box)
    cancel_button.setObjectName("DialogSecondaryButton")
    cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)

    message_box.addButton(
        confirm_button,
        QMessageBox.ButtonRole.DestructiveRole,
    )
    message_box.addButton(
        cancel_button,
        QMessageBox.ButtonRole.RejectRole,
    )

    message_box.setDefaultButton(cancel_button)
    message_box.setEscapeButton(cancel_button)

    message_box.exec()

    return message_box.clickedButton() == confirm_button
