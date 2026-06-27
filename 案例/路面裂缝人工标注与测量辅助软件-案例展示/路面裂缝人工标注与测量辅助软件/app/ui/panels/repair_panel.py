from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QDoubleSpinBox, QListWidget, QMessageBox
from app.ui.widgets import PanelCard, primary_button, InfoBox
from app.core.repair import RepairMaterialEstimator
from app.core.geometry import polyline_length_real


class RepairPanel(QWidget):
    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent); self.state=state; self.storage=storage; self.canvas=canvas
        layout=QVBoxLayout(self); card=PanelCard("修复估算舱")
        self.method=QComboBox(); self.method.addItems(RepairMaterialEstimator.METHODS)
        card.layout.addWidget(QLabel("修复方式")); card.layout.addWidget(self.method)
        rec=QPushButton("按等级自动推荐方式"); rec.clicked.connect(self.recommend); card.layout.addWidget(rec)
        est=primary_button("估算选中裂缝材料用量"); est.clicked.connect(self.estimate); card.layout.addWidget(est)
        batch=QPushButton("批量估算当前任务全部裂缝"); batch.clicked.connect(self.batch); card.layout.addWidget(batch)
        self.list=QListWidget(); card.layout.addWidget(QLabel("维修材料清单")); card.layout.addWidget(self.list)
        self.info=InfoBox("标注结果可直接转为材料估算：灌缝胶按体积估算，罩面与铣刨按面积/厚度估算。")
        card.layout.addWidget(self.info); layout.addWidget(card)
        self.state.selection_changed.connect(self.refresh); self.canvas.canvas_changed.connect(self.refresh) if self.canvas else None; self.refresh()

    def recommend(self):
        c=self.state.selected_crack()
        if not c: return
        self.method.setCurrentText(RepairMaterialEstimator.recommend(c.severity,c.crack_type)); self.info.setText(f"已推荐：{self.method.currentText()}")

    def estimate(self):
        c=self.state.selected_crack(); task=self.state.current_task
        if not c or not task: return
        length=polyline_length_real(c.points, task.meter_per_pixel); length=length if task.meter_per_pixel else length/180
        method,amount,unit=RepairMaterialEstimator.estimate_for_crack(length,c.avg_width_mm,c.severity,c.crack_type,self.method.currentText())
        c.repair_method=method; c.material_amount=amount; c.material_unit=unit
        self.storage.upsert_task(task); self.refresh(); QMessageBox.information(self,'估算完成',f'{method}：{amount:.2f}{unit}')

    def batch(self):
        task=self.state.current_task
        if not task: return
        for c in task.cracks:
            length=polyline_length_real(c.points, task.meter_per_pixel); length=length if task.meter_per_pixel else length/180
            method,amount,unit=RepairMaterialEstimator.estimate_for_crack(length,c.avg_width_mm,c.severity,c.crack_type,None)
            c.repair_method=method; c.material_amount=amount; c.material_unit=unit
        self.storage.upsert_task(task); self.refresh(); QMessageBox.information(self,'批量完成',f'已估算 {len(task.cracks)} 条裂缝的材料用量')

    def refresh(self):
        self.list.clear(); task=self.state.current_task
        if not task: return
        total={}
        for c in task.cracks:
            self.list.addItem(f"{c.crack_id}｜{c.repair_method}｜{c.material_amount:.2f}{c.material_unit}｜{c.severity}")
            total[(c.repair_method,c.material_unit)] = total.get((c.repair_method,c.material_unit),0)+c.material_amount
        summary='\n'.join([f'{k[0]}：{v:.2f}{k[1]}' for k,v in total.items()]) or '暂无材料清单'
        self.info.setText('材料汇总：\n'+summary)
