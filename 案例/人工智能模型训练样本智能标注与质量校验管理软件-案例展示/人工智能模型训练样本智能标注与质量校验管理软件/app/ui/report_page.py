from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QLabel, QMessageBox, QComboBox, QTextEdit
from pathlib import Path
from app.ui.utils import page_root, fill_table, make_project_combo, secondary
from app.services.dataset_service import list_projects
from app.services.report_service import generate_report, list_reports


class ReportPage(QWidget):
    def __init__(self, user: dict):
        super().__init__(); self.user=user
        root,self.layout=page_root('报告生成中心')
        wrap=QVBoxLayout(self); wrap.setContentsMargins(0,0,0,0); wrap.addWidget(root)
        bar=QHBoxLayout(); self.project_combo=make_project_combo(list_projects()); self.project_combo.currentIndexChanged.connect(self.refresh)
        self.report_type=QComboBox(); self.report_type.addItems(['数据集导入体检报告','标注任务进度报告','智能预标注采用率报告','自动质量校验报告','多人一致性分析报告','Ground Truth 抽检报告','返工处理报告','标注员绩效画像报告','标签分布分析报告','数据集健康度报告','数据集版本交付报告','训练格式导出说明书'])
        gen=QPushButton('生成报告'); gen.clicked.connect(self.generate)
        openbtn=secondary(QPushButton('预览选中报告')); openbtn.clicked.connect(self.preview)
        for w in [QLabel('项目'),self.project_combo,QLabel('报告类型'),self.report_type,gen,openbtn]: bar.addWidget(w)
        bar.addStretch(); self.layout.addLayout(bar)
        self.table=QTableWidget(); self.layout.addWidget(self.table,1)
        self.preview_text=QTextEdit(); self.preview_text.setReadOnly(True); self.layout.addWidget(QLabel('报告预览')); self.layout.addWidget(self.preview_text,1)

    def refresh(self):
        rows=list_reports(self.project_combo.currentData()) if self.project_combo.currentData() else []
        fill_table(self.table, rows, [('id','ID'),('report_type','类型'),('title','标题'),('file_path','文件路径'),('conclusion','结论'),('created_by','创建人'),('created_at','时间')])

    def generate(self):
        path=generate_report(self.project_combo.currentData(), self.report_type.currentText(), self.user['username'])
        QMessageBox.information(self,'报告已生成',f'报告文件已生成：\n{path}')
        self.refresh()

    def preview(self):
        row=self.table.currentRow()
        if row<0: QMessageBox.warning(self,'未选择报告','请先选择一条报告记录。'); return
        path=Path(self.table.item(row,3).text())
        self.preview_text.setText(path.read_text(encoding='utf-8') if path.exists() else '报告文件不存在。')
