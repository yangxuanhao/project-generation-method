from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QMessageBox
from app.ui.widgets import PanelCard, primary_button, danger_button, InfoBox
from app.core.width_gauge import CrackWidthGauge
from app.core.auto_detect import CrackAutoDetector


class WidthPanel(QWidget):
    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.storage = storage
        self.canvas = canvas
        layout = QVBoxLayout(self)
        card = PanelCard('宽度卡尺舱')
        btn = primary_button('进入宽度卡尺模式')
        btn.clicked.connect(lambda: self.state.set_mode('宽度卡尺'))
        card.layout.addWidget(btn)

        auto_btn = QPushButton('自动估算最窄/中间/最宽三处宽度')
        auto_btn.clicked.connect(self.auto_estimate)
        card.layout.addWidget(auto_btn)

        clear = QPushButton('清空选中裂缝宽度采样')
        clear.clicked.connect(self.clear_samples)
        card.layout.addWidget(clear)

        delete_line = danger_button('删除选中标注线')
        delete_line.clicked.connect(self.delete_selected_line)
        card.layout.addWidget(delete_line)

        self.list = QListWidget()
        card.layout.addWidget(QLabel('采样点列表'))
        card.layout.addWidget(self.list)
        self.info = InfoBox(
            '先在浏览模式选择人工或自动裂缝，再自动估算。系统会沿裂缝多点采样，保留最窄、中间位置、最宽三处宽度。'
        )
        card.layout.addWidget(self.info)
        layout.addWidget(card)
        self.state.selection_changed.connect(self.refresh)
        self.canvas.canvas_changed.connect(self.refresh) if self.canvas else None
        self.refresh()

    def auto_estimate(self):
        crack = self.state.selected_crack()
        task = self.state.current_task
        if not crack or not task:
            QMessageBox.information(self, '提示', '请先选择一条人工标注或自动识别裂缝')
            return
        samples = CrackAutoDetector.estimate_widths(task.image_path, crack, task.meter_per_pixel)
        if not samples:
            QMessageBox.warning(self, '估算失败', '未能自动估算宽度，请使用人工卡尺或重新标定比例尺')
            return
        crack.width_samples = samples
        if self.canvas:
            self.canvas.refresh_all_measurements()
            self.canvas.canvas_changed.emit()
            self.canvas.update()
        self.storage.upsert_task(task)
        self.refresh()
        vals = [s.width_mm for s in samples]
        QMessageBox.information(
            self,
            '估算完成',
            f'已基于裂缝线生成三处宽度采样：\n'
            f'最窄：{min(vals):.2f}mm\n'
            f'中间：{vals[len(vals)//2]:.2f}mm\n'
            f'最宽：{max(vals):.2f}mm'
        )

    def clear_samples(self):
        crack = self.state.selected_crack()
        if not crack:
            return
        crack.width_samples.clear()
        if self.canvas:
            self.canvas.refresh_all_measurements()
            self.canvas.canvas_changed.emit()
        self.storage.upsert_task(self.state.current_task)
        self.refresh()
        QMessageBox.information(self, '已清空', '该裂缝宽度采样已清空')

    def delete_selected_line(self):
        if not self.canvas:
            return
        ok, msg = self.canvas.delete_selected_any_annotation()
        self.refresh()
        QMessageBox.information(self, '删除标注线', msg)

    def refresh(self):
        self.list.clear()
        crack = self.state.selected_crack()
        task = self.state.current_task
        if not crack:
            self.info.setText('未选择裂缝。请先在浏览模式点击裂缝线或在右侧卡片中选择。')
            return
        labels = ['最窄参考', '中间参考', '最宽参考']
        for i, s in enumerate(crack.width_samples, 1):
            label = labels[i - 1] if len(crack.width_samples) == 3 and i <= 3 else f'采样{i}'
            self.list.addItem(f'{label}：{s.width_mm:.2f} mm｜{s.created_at}')
        length_text = '0.00'
        if task and crack.points:
            length_px = sum((((crack.points[i][0]-crack.points[i-1][0])**2 + (crack.points[i][1]-crack.points[i-1][1])**2)**0.5) for i in range(1, len(crack.points)))
            length_text = f'{length_px*task.meter_per_pixel:.2f} 米' if task.meter_per_pixel else f'{length_px:.1f} 像素'
        vals = [s.width_mm for s in crack.width_samples]
        width_detail = '暂无宽度采样'
        if vals:
            width_detail = f'最窄：{min(vals):.2f}mm｜中间：{vals[len(vals)//2]:.2f}mm｜最宽：{max(vals):.2f}mm'
        self.info.setText(
            f'{crack.crack_id}\n'
            f'来源：{crack.source}\n'
            f'长度：{length_text}\n'
            f'{width_detail}\n'
            f'平均宽度：{crack.avg_width_mm:.2f}mm\n'
            f'最大宽度：{crack.max_width_mm:.2f}mm\n'
            f'状态：{CrackWidthGauge.status_text(crack.max_width_mm)}'
        )
