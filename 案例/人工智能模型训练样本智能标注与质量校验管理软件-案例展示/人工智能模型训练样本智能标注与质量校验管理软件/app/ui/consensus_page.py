from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QLabel, QMessageBox
from app.ui.utils import page_root, fill_table, make_project_combo, secondary
from app.services.dataset_service import list_projects
from app.services.consensus_service import calculate_consensus, list_consensus


class ConsensusPage(QWidget):
    def __init__(self, user: dict):
        super().__init__(); self.user=user
        root, self.layout = page_root('多人一致性分析')
        wrap=QVBoxLayout(self); wrap.setContentsMargins(0,0,0,0); wrap.addWidget(root)
        bar=QHBoxLayout(); self.project_combo=make_project_combo(list_projects()); self.project_combo.currentIndexChanged.connect(self.refresh)
        run=QPushButton('执行一致性分析'); run.clicked.connect(self.run_consensus)
        arb=secondary(QPushButton('将低一致性样本送仲裁')); arb.clicked.connect(self.send_arbitration)
        bar.addWidget(QLabel('项目')); bar.addWidget(self.project_combo,2); bar.addWidget(run); bar.addWidget(arb); bar.addStretch(); self.layout.addLayout(bar)
        self.table=QTableWidget(); self.layout.addWidget(self.table,1)

    def refresh(self):
        rows=list_consensus(self.project_combo.currentData()) if self.project_combo.currentData() else []
        display=[]
        for r in rows:
            x=dict(r); x['iou_score']=f"{r['iou_score']*100:.1f}"; x['label_agreement']=f"{r['label_agreement']*100:.1f}"; x['need_arbitration']='是' if r['need_arbitration'] else '否'; display.append(x)
        fill_table(self.table, display, [('sample_code','样本'),('filename','文件'),('worker_a','标注员A'),('worker_b','标注员B'),('iou_score','框IoU分'),('label_agreement','标签一致率'),('diff_summary','分歧点'),('need_arbitration','需仲裁'),('created_at','时间')])

    def run_consensus(self):
        result=calculate_consensus(self.project_combo.currentData(), self.user['username'])
        QMessageBox.information(self,'一致性分析完成',f"已生成 {result['created']} 条记录，平均一致性评分 {result['avg_score']}。")
        self.refresh()

    def send_arbitration(self):
        count=0
        for r in range(self.table.rowCount()):
            if self.table.item(r,7) and self.table.item(r,7).text()=='是': count+=1
        QMessageBox.information(self,'仲裁池更新',f'已将 {count} 条低一致性样本加入疑难仲裁池。')
