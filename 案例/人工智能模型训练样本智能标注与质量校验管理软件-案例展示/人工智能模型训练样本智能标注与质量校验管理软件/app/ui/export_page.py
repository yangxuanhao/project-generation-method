from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QLabel, QMessageBox, QTextEdit, QFrame, QSplitter, QGridLayout
from PyQt6.QtCore import Qt
from app.ui.utils import page_root, fill_table, make_project_combo, secondary, success, attach_page, title_label, pill
from app.widgets.visual_widgets import DonutGauge, MiniBarChart, ChecklistWidget, WorkflowCard, PipelineWidget
from app.services.dataset_service import list_projects, dashboard_metrics
from app.services.export_service import delivery_check, export_yolo, export_coco, export_pascal_voc, export_text_jsonl
from app.core.database import fetch_all


class ExportPage(QWidget):
    def __init__(self, user: dict):
        super().__init__(); self.user=user
        root,self.layout=page_root('训练格式导出中心', '不是“点按钮导出文件”，而是执行交付门禁、数据划分、格式适配和导出留痕。')
        attach_page(self, root)
        bar=QFrame(); bar.setProperty('card', True); bl=QHBoxLayout(bar); bl.setContentsMargins(14,10,14,10)
        self.project_combo=make_project_combo(list_projects()); self.project_combo.currentIndexChanged.connect(self.refresh)
        check=QPushButton('执行交付前检查'); check.clicked.connect(self.run_check)
        yolo=success(QPushButton('导出 YOLO')); yolo.clicked.connect(lambda:self.export('yolo'))
        coco=QPushButton('导出 COCO JSON'); coco.clicked.connect(lambda:self.export('coco'))
        voc=QPushButton('导出 Pascal VOC'); voc.clicked.connect(lambda:self.export('voc'))
        jsonl=QPushButton('导出文本 JSONL'); jsonl.clicked.connect(lambda:self.export('jsonl'))
        for w in [QLabel('项目'),self.project_combo,check,yolo,coco,voc,jsonl]: bl.addWidget(w)
        bl.addStretch(); self.layout.addWidget(bar)

        top = QSplitter(Qt.Orientation.Horizontal)
        gate_card = QFrame(); gate_card.setProperty('card', True); gl=QVBoxLayout(gate_card)
        gl.addWidget(title_label('交付门禁', '任一阻断项未通过时仍可演示导出，但系统会在导出记录中保留风险说明。'))
        self.gate = ChecklistWidget([]); gl.addWidget(self.gate)
        self.check_text=QTextEdit(); self.check_text.setReadOnly(True); self.check_text.setMaximumHeight(120); gl.addWidget(self.check_text)
        top.addWidget(gate_card)
        visual = QFrame(); visual.setProperty('card', True); vl=QVBoxLayout(visual)
        vl.addWidget(title_label('训练 / 验证 / 测试划分', '用于检查划分比例是否完整、类别是否均衡。'))
        charts=QHBoxLayout(); self.split_chart=MiniBarChart('数据划分', [('train',80),('val',10),('test',10)], '%'); self.health=DonutGauge('交付健康度',0,'分')
        charts.addWidget(self.split_chart); charts.addWidget(self.health); vl.addLayout(charts)
        self.flow = PipelineWidget([('检查',0),('冻结',0),('导出',0),('报告',0)])
        vl.addWidget(self.flow)
        top.addWidget(visual)
        top.setSizes([700, 760])
        self.layout.addWidget(top)

        grid=QGridLayout(); grid.setSpacing(12); self.layout.addLayout(grid)
        self.format_cards=[]
        for i,(fmt,desc,tone) in enumerate([
            ('YOLO','目标检测训练：images / labels / data.yaml','blue'),('COCO JSON','检测/分割训练：instances_train.json','green'),
            ('Pascal VOC','XML 标注与 JPEGImages 目录','amber'),('JSONL','文本分类、指令微调、偏好数据','blue')]):
            c=WorkflowCard(fmt,'可导出',desc,fmt,tone); c.clicked.connect(lambda f: QMessageBox.information(self,'格式说明',f'已选中 {f}，导出时会写入本地 demo/exports 目录并生成记录。'))
            grid.addWidget(c,0,i); self.format_cards.append(c)
        self.table=QTableWidget(); self.layout.addWidget(QLabel('导出留痕记录')); self.layout.addWidget(self.table,1)

    def refresh(self):
        pid=self.project_combo.currentData()
        if not pid: return
        metrics = dashboard_metrics(pid)
        self.health.set_value(float(metrics.get('health_score',0)))
        rows=fetch_all('SELECT * FROM export_records WHERE project_id=? ORDER BY id DESC',(pid,))
        fill_table(self.table, rows, [('format','格式'),('output_path','输出路径'),('check_result','交付检查'),('created_by','操作人'),('created_at','时间')])
        self.flow.set_stages([('检查', 1 if self.check_text.toPlainText() else 0), ('版本', metrics.get('version_total',0)), ('导出', len(rows)), ('报告', len(fetch_all('SELECT id FROM reports WHERE project_id=?',(pid,))))])
        self.update_gate()

    def update_gate(self):
        pid=self.project_combo.currentData()
        if not pid: return
        ok,problems=delivery_check(pid)
        checks = [
            ('无未标注样本', not any('未标注样本' in p for p in problems), '未标注样本会影响训练集完整度'),
            ('无待质检样本', not any('未质检样本' in p for p in problems), '所有样本应至少完成自动/人工质检'),
            ('返工任务已关闭', not any('返工样本' in p for p in problems), '返工样本不应进入交付包'),
            ('健康度达到阈值', not any('健康度' in p for p in problems), '建议 80 分以上再冻结交付'),
            ('标签分布可解释', True, '系统将输出标签分布与长尾提示'),
            ('划分比例完整', True, '默认 80 / 10 / 10，可在版本页调整'),
        ]
        self.gate.set_items(checks)

    def run_check(self):
        ok,problems=delivery_check(self.project_combo.currentData())
        self.check_text.setText('交付检查通过，可以导出训练集。' if ok else '交付检查发现问题：\n- ' + '\n- '.join(problems))
        self.update_gate()
        QMessageBox.information(self,'交付检查完成','通过' if ok else f'发现 {len(problems)} 个风险项，请根据门禁提示处理。')
        self.refresh()

    def export(self, fmt):
        pid=self.project_combo.currentData()
        ok, problems = delivery_check(pid)
        if fmt=='yolo': path=export_yolo(pid,self.user['username'])
        elif fmt=='coco': path=export_coco(pid,self.user['username'])
        elif fmt=='voc': path=export_pascal_voc(pid,self.user['username'])
        else: path=export_text_jsonl(pid,self.user['username'])
        risk = '交付检查通过' if ok else '带风险导出：' + '；'.join(problems[:3])
        self.check_text.setText(risk)
        QMessageBox.information(self,'导出完成',f'训练格式已导出：\n{path}\n\n{risk}')
        self.refresh()
