from __future__ import annotations

from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QMessageBox, QFileDialog
from app.ui.widgets import PanelCard, primary_button, InfoBox
from app.core.report import CrackReportGenerator
from app.core.quality import AnnotationQualityChecker


class ReportPanel(QWidget):
    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent); self.state=state; self.storage=storage; self.project_root=Path(project_root); self.canvas=canvas
        self.generator=CrackReportGenerator(self.project_root/'exports')
        layout=QVBoxLayout(self); card=PanelCard('成果报告舱')
        check=QPushButton('导出前完整性检查'); check.clicked.connect(self.check_quality); card.layout.addWidget(check)
        json_btn=QPushButton('导出JSON标注数据'); json_btn.clicked.connect(self.export_json); card.layout.addWidget(json_btn)
        csv_btn=QPushButton('导出CSV测量表'); csv_btn.clicked.connect(self.export_csv); card.layout.addWidget(csv_btn)
        txt_btn=primary_button('生成路面裂缝测量分析报告'); txt_btn.clicked.connect(self.export_report); card.layout.addWidget(txt_btn)
        snap_btn=QPushButton('导出当前画布标注快照'); snap_btn.clicked.connect(self.export_snapshot); card.layout.addWidget(snap_btn)
        self.list=QListWidget(); card.layout.addWidget(QLabel('导出记录')); card.layout.addWidget(self.list)
        self.info=InfoBox('报告包含任务信息、比例尺、裂缝数量、长度宽度、等级分布、复核记录和材料估算。')
        card.layout.addWidget(self.info); layout.addWidget(card)

    def _tasks(self): return self.state.tasks
    def _record(self,path): self.list.addItem(str(path)); self.info.setText(f'已生成：\n{path}')

    def check_quality(self):
        lines=[]
        for task in self._tasks():
            score, details=AnnotationQualityChecker.score(task); lines.append(f'{task.road_name}：{score}分'); lines.extend(['  '+d for d in details[:5]])
        QMessageBox.information(self,'完整性检查','\n'.join(lines) if lines else '暂无任务')

    def export_json(self):
        path=self.generator.export_json(self._tasks()); self._record(path); QMessageBox.information(self,'导出成功',str(path))

    def export_csv(self):
        path=self.generator.export_csv(self._tasks()); self._record(path); QMessageBox.information(self,'导出成功',str(path))

    def export_report(self):
        path=self.generator.export_txt_report(self._tasks()); self._record(path); QMessageBox.information(self,'报告完成',str(path))

    def export_snapshot(self):
        if not self.canvas: return
        path=self.project_root/'exports'/f'canvas_snapshot.png'
        image=self.canvas.grab(); image.save(str(path)); self._record(path); QMessageBox.information(self,'快照完成',str(path))
