from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QFileDialog, QLabel, QProgressBar, QMessageBox, QFrame, QSplitter
from PyQt6.QtCore import Qt
from app.ui.utils import page_root, fill_table, secondary, make_project_combo, attach_page, title_label
from app.widgets.visual_widgets import PipelineWidget, RiskHeatmap, ChecklistWidget, MiniBarChart
from app.services.dataset_service import list_projects
from app.services.import_service import import_images, import_text_csv, inspect_image_folder, inspect_text_csv


class ImportPage(QWidget):
    def __init__(self, user: dict):
        super().__init__(); self.user = user
        root, self.layout = page_root('样本导入与数据体检', '导入即体检：重复、损坏、尺寸异常、空文本、标签缺失和结构问题会进入风险队列。')
        attach_page(self, root)
        bar = QFrame(); bar.setProperty('card', True); bl=QHBoxLayout(bar); bl.setContentsMargins(14,10,14,10)
        self.project_combo = make_project_combo(list_projects())
        img_btn = QPushButton('导入图片文件夹并体检'); img_btn.clicked.connect(self.import_image_folder)
        txt_btn = QPushButton('导入文本CSV并体检'); txt_btn.clicked.connect(self.import_csv)
        demo_btn = secondary(QPushButton('仅执行体检预览')); demo_btn.clicked.connect(self.inspect_only)
        for w in [QLabel('目标项目'), self.project_combo, img_btn, txt_btn, demo_btn]: bl.addWidget(w)
        bl.addStretch(); self.layout.addWidget(bar)
        self.progress = QProgressBar(); self.progress.setValue(0); self.layout.addWidget(self.progress)
        self.flow = PipelineWidget([('读取',0),('体检',0),('入库',0),('报告',0)])
        flow_card=QFrame(); flow_card.setProperty('card', True); fl=QVBoxLayout(flow_card); fl.addWidget(title_label('导入流水线', '真实系统将导入过程拆成可追踪状态，并允许异常项定位到具体样本。')); fl.addWidget(self.flow)
        self.layout.addWidget(flow_card)
        splitter=QSplitter(Qt.Orientation.Horizontal)
        left=QFrame(); left.setProperty('card', True); ll=QVBoxLayout(left); ll.addWidget(title_label('体检风险摘要', '异常项会进入返工/人工确认，不直接进入可交付样本池。'))
        self.risk=RiskHeatmap('体检问题热力', {})
        self.checklist=ChecklistWidget([])
        ll.addWidget(self.risk); ll.addWidget(QLabel('入库门禁')); ll.addWidget(self.checklist)
        splitter.addWidget(left)
        right=QFrame(); right.setProperty('card', True); rl=QVBoxLayout(right)
        self.summary = QLabel('选择数据后将自动识别重复、近似重复、损坏、尺寸异常、空文本、标签缺失等问题。')
        self.summary.setWordWrap(True); rl.addWidget(self.summary)
        self.table = QTableWidget(); rl.addWidget(self.table, 1)
        splitter.addWidget(right); splitter.setSizes([420, 980])
        self.layout.addWidget(splitter, 1)

    def refresh(self):
        cur=self.project_combo.currentData(); self.project_combo.clear()
        for p in list_projects(): self.project_combo.addItem(f"{p['code']}｜{p['name']}", p['id'])
        if cur:
            idx=self.project_combo.findData(cur)
            if idx>=0: self.project_combo.setCurrentIndex(idx)

    def import_image_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '选择图片文件夹')
        if not folder: return
        self.progress.setValue(25); self.flow.set_stages([('读取',1),('体检',0),('入库',0),('报告',0)])
        rows = import_images(self.project_combo.currentData(), folder, self.user['username'])
        self.progress.setValue(100); self.flow.set_stages([('读取',len(rows)),('体检',len(rows)),('入库',sum(1 for r in rows if not r.get('issues'))),('报告',1)])
        self.show_image_rows(rows)
        QMessageBox.information(self, '导入完成', f'共导入/体检 {len(rows)} 张图片，异常项可在表格中定位。')

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, '选择CSV样本表', '', 'CSV Files (*.csv)')
        if not path: return
        self.progress.setValue(30)
        rows = import_text_csv(self.project_combo.currentData(), path, self.user['username'])
        self.progress.setValue(100); self.flow.set_stages([('读取',len(rows)),('体检',len(rows)),('入库',sum(1 for r in rows if not r.get('issues'))),('报告',1)])
        fill_table(self.table, rows, [('line','行号'),('text','文本'),('label','标签'),('status','体检状态'),('issues','问题')])
        risk_counts={}
        for r in rows:
            for part in str(r.get('issues','')).split(';'):
                if part: risk_counts[part]=risk_counts.get(part,0)+1
        self.risk.set_data(risk_counts or {'无异常': len(rows)})
        self.checklist.set_items([('文本非空', not any('空' in str(r.get('issues','')) for r in rows), '空文本会阻断进入训练集'), ('标签字段存在', not any('标签' in str(r.get('issues','')) for r in rows), '标签缺失需补齐'), ('结构一致', True, 'CSV 字段已成功解析')])
        self.summary.setText(f'文本导入完成：{len(rows)} 条，异常 {sum(1 for r in rows if r["issues"])} 条。')

    def inspect_only(self):
        folder = QFileDialog.getExistingDirectory(self, '选择图片文件夹用于体检预览')
        if not folder: return
        rows = inspect_image_folder(folder)
        self.show_image_rows(rows)
        self.progress.setValue(100); self.flow.set_stages([('读取',len(rows)),('体检',len(rows)),('入库',0),('报告',1)])

    def show_image_rows(self, rows):
        display = [{**r, 'issues': ';'.join(r.get('issues', []))} for r in rows]
        fill_table(self.table, display, [('filename','文件名'),('width','宽'),('height','高'),('status','体检状态'),('issues','问题')])
        risk_counts={}
        for r in rows:
            for i in r.get('issues',[]): risk_counts[i]=risk_counts.get(i,0)+1
        self.risk.set_data(risk_counts or {'无异常': len(rows)})
        self.checklist.set_items([('图片可读取', not any('损坏' in ';'.join(r.get('issues',[])) for r in rows), '损坏文件不会入库'), ('尺寸满足要求', not any('尺寸' in ';'.join(r.get('issues',[])) for r in rows), '过小/过大样本需人工确认'), ('重复样本已识别', True, '重复项会打上风险标签')])
        self.summary.setText(f'图像体检摘要：总数 {len(rows)}，异常/待确认 {sum(1 for r in rows if r.get("issues"))}，重复 {sum(1 for r in rows if any("重复" in i for i in r.get("issues", [])))}。')
