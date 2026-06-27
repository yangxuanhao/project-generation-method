from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSlider, QMessageBox
from PyQt6.QtCore import Qt
from app.ui.widgets import PanelCard, InfoBox


class SnapPanel(QWidget):
    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent); self.state=state; self.storage=storage; self.canvas=canvas
        layout=QVBoxLayout(self); card=PanelCard("磁吸辅助舱")
        self.toggle=QPushButton("开启磁吸辅助"); self.toggle.clicked.connect(self.switch); card.layout.addWidget(self.toggle)
        self.slider=QSlider(Qt.Orientation.Horizontal); self.slider.setRange(3,40); self.slider.setValue(10); self.slider.valueChanged.connect(self.radius_changed)
        card.layout.addWidget(QLabel("吸附半径")); card.layout.addWidget(self.slider)
        draw=QPushButton("开启磁吸后进入折线描绘"); draw.clicked.connect(self.draw_with_snap); card.layout.addWidget(draw)
        self.info=InfoBox("磁吸辅助会在点击点附近寻找更暗的裂缝中心点，减少人工点位偏差。")
        card.layout.addWidget(self.info); layout.addWidget(card)

    def switch(self):
        self.state.snap_assistant.set_enabled(not self.state.snap_assistant.enabled)
        self.toggle.setText("关闭磁吸辅助" if self.state.snap_assistant.enabled else "开启磁吸辅助")
        self.info.setText(self.state.snap_assistant.last_message)
        QMessageBox.information(self,"磁吸状态", self.state.snap_assistant.last_message)

    def radius_changed(self, value):
        self.state.snap_assistant.set_radius(value); self.info.setText(self.state.snap_assistant.last_message)

    def draw_with_snap(self):
        self.state.snap_assistant.set_enabled(True); self.toggle.setText("关闭磁吸辅助"); self.state.set_mode("折线裂缝")
