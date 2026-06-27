from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QProgressBar, QMessageBox
from app.ui.widgets import PanelCard, primary_button, InfoBox
from app.core.statistics import RoadSectionStatistics


class StatisticsPanel(QWidget):
    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent); self.state=state; self.storage=storage; self.canvas=canvas
        layout=QVBoxLayout(self); card=PanelCard("路段统计舱")
        btn=primary_button("生成路段病害统计")
        btn.clicked.connect(self.generate); card.layout.addWidget(btn)
        self.risk=QProgressBar(); self.risk.setRange(0,100); card.layout.addWidget(QLabel('病害指数')); card.layout.addWidget(self.risk)
        self.list=QListWidget(); card.layout.addWidget(QLabel('统计结果')); card.layout.addWidget(self.list)
        self.info=InfoBox('统计会汇总所有任务，形成路段级裂缝总长、网裂面积、等级分布和养护优先级。')
        card.layout.addWidget(self.info); layout.addWidget(card)

    def generate(self):
        stat=RoadSectionStatistics.summarize_tasks(self.state.tasks)
        self.list.clear()
        for k,v in stat.items():
            if isinstance(v,dict): self.list.addItem(f'{k}：{v}')
            elif isinstance(v,float): self.list.addItem(f'{k}：{v:.2f}')
            else: self.list.addItem(f'{k}：{v}')
        self.risk.setValue(stat['病害指数'])
        advice = '优先修复' if stat['病害指数']>=70 else ('近期养护' if stat['病害指数']>=40 else '日常巡查')
        self.info.setText(f"路段病害指数：{stat['病害指数']}\n建议：{advice}\n裂缝总数：{stat['裂缝总数']}\n较重及严重数量：{stat['较重及严重数量']}")
        QMessageBox.information(self,'统计完成',f"病害指数：{stat['病害指数']}，建议：{advice}")
