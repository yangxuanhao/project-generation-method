from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QMessageBox
from app.ui.widgets import PanelCard, primary_button, danger_button, InfoBox


class RegionPanel(QWidget):
    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent); self.state=state; self.storage=storage; self.canvas=canvas
        layout=QVBoxLayout(self); card=PanelCard("网裂圈选舱")
        btn=primary_button("进入网裂区域圈选模式"); btn.clicked.connect(lambda: self.state.set_mode("网裂圈选")); card.layout.addWidget(btn)
        finish=QPushButton("闭合并生成网裂区域"); finish.clicked.connect(lambda: self.canvas.finish_region() if self.canvas else None); card.layout.addWidget(finish)
        undo=QPushButton("撤销区域顶点"); undo.clicked.connect(lambda: self.canvas.undo_last_point() if self.canvas else None); card.layout.addWidget(undo)
        clear=QPushButton("清空当前任务所有网裂区"); clear.clicked.connect(self.clear_regions); card.layout.addWidget(clear)
        delete_line=danger_button("删除选中标注线"); delete_line.clicked.connect(self.delete_selected_line); card.layout.addWidget(delete_line)
        self.list=QListWidget(); card.layout.addWidget(QLabel("网裂区域列表")); card.layout.addWidget(self.list)
        self.info=InfoBox("左键圈选网裂或龟裂区域，右键闭合，也可点击“闭合并生成网裂区域”。切换到诊断、复核、统计等页面时，系统会自动停止圈选模式，避免误触继续标注。")
        card.layout.addWidget(self.info); layout.addWidget(card)
        self.state.task_changed.connect(self.refresh); self.canvas.canvas_changed.connect(self.refresh) if self.canvas else None; self.refresh()

    def delete_selected_line(self):
        if not self.canvas:
            return
        ok, msg = self.canvas.delete_selected_any_annotation()
        self.refresh()
        QMessageBox.information(self, "删除标注线", msg)

    def clear_regions(self):
        task=self.state.current_task
        if not task: return
        task.regions.clear(); self.storage.upsert_task(task); self.canvas.canvas_changed.emit() if self.canvas else None; self.canvas.update() if self.canvas else None; self.refresh(); QMessageBox.information(self,"已清空","当前任务网裂区域已清空")

    def refresh(self):
        self.list.clear(); task=self.state.current_task
        if not task: return
        for r in task.regions: self.list.addItem(f"{r.region_id}｜面积{r.area_m2:.2f}㎡｜密度{r.density:.2f}｜{r.severity}")
