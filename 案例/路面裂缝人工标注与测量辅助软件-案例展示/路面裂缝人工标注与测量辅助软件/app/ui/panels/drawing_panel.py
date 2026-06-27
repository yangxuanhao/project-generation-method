from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMessageBox
from app.ui.widgets import PanelCard, primary_button, danger_button, InfoBox


class DrawingPanel(QWidget):
    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.storage = storage
        self.canvas = canvas
        layout = QVBoxLayout(self)
        card = PanelCard('裂缝描绘舱')
        btn = primary_button('进入折线裂缝描绘模式')
        btn.clicked.connect(lambda: self.state.set_mode('折线裂缝'))
        card.layout.addWidget(btn)
        finish = QPushButton('结束当前裂缝')
        finish.clicked.connect(lambda: self.canvas.finish_polyline() if self.canvas else None)
        card.layout.addWidget(finish)
        undo = QPushButton('撤销上一个节点')
        undo.clicked.connect(lambda: self.canvas.undo_last_point() if self.canvas else None)
        card.layout.addWidget(undo)
        smooth = QPushButton('平滑选中裂缝')
        smooth.clicked.connect(self.smooth)
        card.layout.addWidget(smooth)
        delete = danger_button('删除选中裂缝')
        delete.clicked.connect(self.delete)
        card.layout.addWidget(delete)
        browse = QPushButton('返回浏览选择模式')
        browse.clicked.connect(lambda: self.state.set_mode('浏览'))
        card.layout.addWidget(browse)
        self.info = InfoBox('左键连续点选裂缝中心线，右键或双击结束。浏览模式下可拖动选中裂缝的节点，便于人工调整自动识别结果。')
        card.layout.addWidget(self.info)
        layout.addWidget(card)
        self.state.selection_changed.connect(self.refresh)
        self.refresh()

    def smooth(self):
        ok = self.canvas.smooth_selected_crack() if self.canvas else False
        QMessageBox.information(self, '线条平滑', '已对裂缝节点进行平滑处理' if ok else '请先选择一条未锁定裂缝')

    def delete(self):
        ok = self.canvas.delete_selected_crack() if self.canvas else False
        QMessageBox.information(self, '删除结果', '已删除选中裂缝' if ok else '没有可删除的裂缝')

    def refresh(self):
        c = self.state.selected_crack()
        if c:
            self.info.setText(
                f'选中裂缝：{c.crack_id}\n'
                f'来源：{c.source}\n'
                f'节点数：{len(c.points)}\n'
                f'类型：{c.crack_type}\n'
                f'等级：{c.severity}\n'
                f'复核：{c.review_status}\n'
                f'提示：在浏览模式下可直接拖动节点。'
            )
