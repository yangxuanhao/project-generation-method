from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QDoubleSpinBox, QMessageBox, QCheckBox, QSlider
from PyQt6.QtCore import Qt
from app.ui.widgets import PanelCard, primary_button, InfoBox
from app.core.calibration import ImageCalibrationEngine


class CalibrationPanel(QWidget):
    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.storage = storage
        self.canvas = canvas
        layout = QVBoxLayout(self)
        card = PanelCard('比例标定舱')
        card.layout.addWidget(QLabel('两点标定：点击按钮后在画布上点两个标尺端点，再输入实际距离。'))
        btn = primary_button('进入两点标定模式')
        btn.clicked.connect(lambda: self.state.set_mode('比例标定'))
        card.layout.addWidget(btn)

        close_calib_btn = QPushButton('关闭两点标定模式')
        close_calib_btn.clicked.connect(self.close_calibration_mode)
        card.layout.addWidget(close_calib_btn)

        self.default_mpp = QDoubleSpinBox()
        self.default_mpp.setRange(0.01, 50)
        self.default_mpp.setValue(0.5)
        self.default_mpp.setSuffix(' 毫米/像素')
        card.layout.addWidget(QLabel('固定相机默认比例'))
        card.layout.addWidget(self.default_mpp)

        default_btn = QPushButton('应用默认比例并重算')
        default_btn.clicked.connect(self.apply_default)
        card.layout.addWidget(default_btn)

        self.ruler_check = QCheckBox('显示图像边缘比例尺')
        self.ruler_check.setChecked(self.state.show_scale_ruler)
        self.ruler_check.toggled.connect(self.state.set_show_scale_ruler)
        card.layout.addWidget(self.ruler_check)

        self.grid_check = QCheckBox('在图像上显示参考网格')
        self.grid_check.setChecked(self.state.show_reference_grid)
        self.grid_check.toggled.connect(self.state.set_show_reference_grid)
        card.layout.addWidget(self.grid_check)

        card.layout.addWidget(QLabel('参考网格透明度'))
        self.grid_opacity = QSlider(Qt.Orientation.Horizontal)
        self.grid_opacity.setRange(0, 100)
        self.grid_opacity.setValue(self.state.reference_grid_opacity)
        self.grid_opacity.valueChanged.connect(self.state.set_reference_grid_opacity)
        card.layout.addWidget(self.grid_opacity)

        card.layout.addWidget(QLabel('标注线透明度'))
        self.line_opacity = QSlider(Qt.Orientation.Horizontal)
        self.line_opacity.setRange(15, 100)
        self.line_opacity.setValue(self.state.overlay_line_opacity)
        self.line_opacity.valueChanged.connect(self.state.set_overlay_line_opacity)
        card.layout.addWidget(self.line_opacity)

        recalc_btn = QPushButton('重新计算全部裂缝量测值')
        recalc_btn.clicked.connect(self.recalculate)
        card.layout.addWidget(recalc_btn)

        delete_btn = QPushButton('删除选中标注线')
        delete_btn.clicked.connect(self.delete_selected)
        card.layout.addWidget(delete_btn)

        self.info = InfoBox()
        card.layout.addWidget(self.info)
        layout.addWidget(card)
        self.state.task_changed.connect(self.refresh)
        self.state.view_flags_changed.connect(self.refresh)
        self.refresh()

    def close_calibration_mode(self):
        self.state.set_mode('浏览')
        if self.canvas:
            self.canvas.calibration_points.clear()
            self.canvas.update()
        QMessageBox.information(self, '两点标定', '已关闭两点标定模式，画布已回到浏览模式。')

    def apply_default(self):
        task = self.state.current_task
        if not task:
            return
        task.meter_per_pixel = self.default_mpp.value() / 1000
        if self.canvas:
            self.canvas.refresh_all_measurements()
            self.canvas.canvas_changed.emit()
            self.canvas.update()
        self.storage.upsert_task(task)
        self.refresh()
        QMessageBox.information(self, '比例已应用', '全部测量值已按默认比例重新计算')

    def recalculate(self):
        if self.canvas:
            self.canvas.refresh_all_measurements()
            self.canvas.canvas_changed.emit()
            self.canvas.update()
        if self.state.current_task:
            self.storage.upsert_task(self.state.current_task)
        self.refresh()
        QMessageBox.information(self, '已重算', '长度、宽度、面积和等级已刷新')

    def delete_selected(self):
        if not self.canvas:
            return
        ok, msg = self.canvas.delete_selected_any_annotation()
        QMessageBox.information(self, '删除标注线', msg if ok else msg)

    def refresh(self):
        task = self.state.current_task
        text = [ImageCalibrationEngine.describe(task.meter_per_pixel) if task else '尚未选择任务']
        text.append(f'图像边缘比例尺：{"显示" if self.state.show_scale_ruler else "隐藏"}')
        text.append(f'图像参考网格：{"显示" if self.state.show_reference_grid else "隐藏"}')
        text.append(f'网格透明度：{self.state.reference_grid_opacity}%')
        text.append(f'标注线透明度：{self.state.overlay_line_opacity}%')
        text.append('参考网格会覆盖在图像上，不再只显示在画布背景中。')
        self.info.setText('\n'.join(text))
