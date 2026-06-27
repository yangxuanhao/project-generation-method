from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt


class MetricCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, title: str, value: str, sub: str = '', key: str = ''):
        super().__init__()
        self.key = key or title
        self.setProperty('card', True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet('color:#64748b;font-size:12px;')
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet('font-size:24px;font-weight:800;color:#0f172a;')
        self.sub_label = QLabel(sub)
        self.sub_label.setStyleSheet('color:#64748b;')
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.sub_label)

    def mousePressEvent(self, event):
        self.clicked.emit(self.key)
        super().mousePressEvent(event)

    def set_value(self, value, sub: str = ''):
        self.value_label.setText(str(value))
        if sub:
            self.sub_label.setText(sub)
