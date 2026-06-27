from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QMessageBox, QListWidget
from app.ui.widgets import PanelCard, primary_button, danger_button, InfoBox
from app.core.severity import CrackSeverityEvaluator
from app.core.geometry import polyline_length_real
from app.core.region_analyzer import CrackRegionAnalyzer


class DiagnosisPanel(QWidget):
    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.storage = storage
        self.canvas = canvas
        layout = QVBoxLayout(self)
        card = PanelCard('病害诊断舱')
        self.type_box = QComboBox()
        self.type_box.addItems(['横向裂缝', '纵向裂缝', '斜向裂缝', '网状裂缝', '龟裂', '块状裂缝', '接缝破损', '沉陷伴生裂缝', '修补边缘裂缝'])
        card.layout.addWidget(QLabel('人工确认裂缝类型'))
        card.layout.addWidget(self.type_box)
        apply = primary_button('采纳/修改类型并重新评估等级')
        apply.clicked.connect(self.apply_type)
        card.layout.addWidget(apply)
        first = QPushButton('自动选择第一条裂缝')
        first.clicked.connect(self.select_first_crack)
        card.layout.addWidget(first)
        explain = QPushButton('显示等级判定依据')
        explain.clicked.connect(self.explain)
        card.layout.addWidget(explain)
        batch = QPushButton('批量诊断裂缝和网裂区域')
        batch.clicked.connect(self.batch)
        card.layout.addWidget(batch)
        delete_line = danger_button('删除选中标注线')
        delete_line.clicked.connect(self.delete_selected_line)
        card.layout.addWidget(delete_line)
        self.summary_list = QListWidget()
        card.layout.addWidget(QLabel('诊断对象汇总'))
        card.layout.addWidget(self.summary_list)
        self.info = InfoBox()
        card.layout.addWidget(self.info)
        layout.addWidget(card)
        self.state.selection_changed.connect(self.refresh)
        self.state.task_changed.connect(self.refresh)
        if self.canvas:
            self.canvas.canvas_changed.connect(self.refresh)
        self.refresh()

    def select_first_crack(self):
        task = self.state.current_task
        if task and task.cracks:
            self.state.select_crack(task.cracks[0].crack_id)
            QMessageBox.information(self, '已选择', f'已选中 {task.cracks[0].crack_id}')
        else:
            QMessageBox.information(self, '暂无裂缝', '当前任务还没有折线裂缝，可先自动标注或人工描绘。')

    def apply_type(self):
        task = self.state.current_task
        c = self.state.selected_crack()
        if task and not c and task.cracks:
            c = task.cracks[0]
            self.state.select_crack(c.crack_id)
        if not c or not task:
            QMessageBox.information(self, '无法诊断', '当前没有可诊断的折线裂缝。网裂区域可使用“批量诊断裂缝和网裂区域”。')
            return
        c.crack_type = self.type_box.currentText()
        reasons = CrackSeverityEvaluator.refresh_crack(c, task.meter_per_pixel)
        task.touch()
        self.storage.upsert_task(task)
        if self.canvas:
            self.canvas.canvas_changed.emit()
            self.canvas.update()
        self.info.setText('\n'.join(reasons))
        self.refresh()
        QMessageBox.information(self, '诊断完成', f'{c.crack_id} 已评估为：{c.severity}')

    def explain(self):
        c = self.state.selected_crack()
        task = self.state.current_task
        if not c or not task:
            QMessageBox.information(self, '未选择裂缝', '请先点击画布裂缝线、右侧卡片或底部轨道选中一条裂缝。')
            return
        reasons = CrackSeverityEvaluator.refresh_crack(c, task.meter_per_pixel)
        length = polyline_length_real(c.points, task.meter_per_pixel)
        length = length if task.meter_per_pixel else length / 180
        QMessageBox.information(
            self,
            '判定依据',
            f'长度：{length:.2f}米\n平均宽度：{c.avg_width_mm:.2f}mm\n最大宽度：{c.max_width_mm:.2f}mm\n类型：{c.crack_type}\n等级：{c.severity}\n\n' + '\n'.join(reasons)
        )

    def batch(self):
        task = self.state.current_task
        if not task:
            return
        crack_count = 0
        for c in task.cracks:
            CrackSeverityEvaluator.refresh_crack(c, task.meter_per_pixel)
            crack_count += 1
        total_len = sum(polyline_length_real(c.points, task.meter_per_pixel) for c in task.cracks)
        if not task.meter_per_pixel:
            total_len = total_len / 180
        region_count = 0
        for r in task.regions:
            r.area_m2 = CrackRegionAnalyzer.area(r.polygon_points, task.meter_per_pixel)
            r.density = CrackRegionAnalyzer.density(total_len, r.area_m2)
            r.severity = CrackRegionAnalyzer.severity(r.area_m2, r.density)
            region_count += 1
        task.touch()
        self.storage.upsert_task(task)
        if self.canvas:
            self.canvas.canvas_changed.emit()
            self.canvas.update()
        self.refresh()
        QMessageBox.information(self, '批量完成', f'已诊断裂缝 {crack_count} 条，网裂区域 {region_count} 个。')

    def delete_selected_line(self):
        if not self.canvas:
            return
        ok, msg = self.canvas.delete_selected_any_annotation()
        self.refresh()
        QMessageBox.information(self, '删除标注线', msg)

    def refresh(self):
        self.summary_list.clear()
        task = self.state.current_task
        if not task:
            self.info.setText('尚未选择任务。')
            return
        for c in task.cracks:
            self.summary_list.addItem(f'裂缝｜{c.crack_id}｜{c.crack_type}｜{c.severity}｜宽度{c.avg_width_mm:.2f}mm')
        for r in task.regions:
            self.summary_list.addItem(f'网裂区｜{r.region_id}｜面积{r.area_m2:.2f}㎡｜密度{r.density:.2f}｜{r.severity}')

        c = self.state.selected_crack()
        if c:
            self.type_box.setCurrentText(c.crack_type if c.crack_type else c.suggestion_type)
            length = polyline_length_real(c.points, task.meter_per_pixel)
            length = length if task.meter_per_pixel else length / 180
            self.info.setText(
                f'当前选中：{c.crack_id}\n'
                f'系统建议：{c.suggestion_type}\n'
                f'当前类型：{c.crack_type}\n'
                f'长度：{length:.2f}米\n'
                f'平均宽度：{c.avg_width_mm:.2f}mm\n'
                f'严重等级：{c.severity}'
            )
        elif task.cracks:
            self.info.setText('当前任务已有裂缝，但未选中。可点击“自动选择第一条裂缝”，或点击画布线段/右侧卡片/底部轨道。')
        elif task.regions:
            self.info.setText('当前任务已有网裂区域。网裂区域不需要选择折线，可点击“批量诊断裂缝和网裂区域”。')
        else:
            pending = len(self.state.region_pending_points)
            if pending >= 3:
                self.info.setText('检测到有未闭合的网裂圈选点。进入本舱时系统会尽量自动闭合，若未生成请回到网裂圈选舱点击“闭合并生成网裂区域”。')
            else:
                self.info.setText('未发现已完成标注。请先进入自动标注舱或裂缝描绘舱生成裂缝对象。')
