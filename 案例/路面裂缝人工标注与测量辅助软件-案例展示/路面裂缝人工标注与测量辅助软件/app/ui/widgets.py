from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QGroupBox, QTextEdit
from PyQt6.QtCore import Qt


def title_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("TitleLabel")
    return label


class PanelCard(QFrame):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("PanelCard")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(10)
        if title:
            self.layout.addWidget(title_label(title))


class InfoBox(QTextEdit):
    def __init__(self, text: str = ""):
        super().__init__()
        self.setReadOnly(True)
        self.setMinimumHeight(80)
        self.setText(text)


def primary_button(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setObjectName("PrimaryButton")
    return b


def success_button(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setObjectName("SuccessButton")
    return b


def danger_button(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setObjectName("DangerButton")
    return b


def make_button_row(*buttons):
    row = QHBoxLayout()
    for b in buttons:
        row.addWidget(b)
    row.addStretch()
    return row


def group_box(title: str, layout) -> QGroupBox:
    box = QGroupBox(title)
    box.setLayout(layout)
    return box
