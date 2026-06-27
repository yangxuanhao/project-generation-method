from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QMessageBox, QFrame, QSplitter, QGridLayout, QLabel, QDateEdit
from PyQt6.QtCore import Qt, QDate
from app.ui.utils import page_root, fill_table, secondary, attach_page, title_label, pill
from app.widgets.visual_widgets import MiniBarChart, DonutGauge, WorkflowCard, PipelineWidget
from app.services.dataset_service import list_projects, create_project, dashboard_metrics


class DatasetPage(QWidget):
    def __init__(self, user: dict):
        super().__init__(); self.user = user
        root, self.layout = page_root('数据集项目管理', '以项目交付状态、样本规模、质量健康度和生产阶段管理数据集，而不是简单增删改查。')
        attach_page(self, root)
        bar = QFrame(); bar.setProperty('card', True); bl=QHBoxLayout(bar); bl.setContentsMargins(14,10,14,10)
        add = QPushButton('创建数据集项目'); add.clicked.connect(self.add_project)
        refresh = secondary(QPushButton('刷新生产态势')); refresh.clicked.connect(self.refresh)
        self.project_chip = pill('项目数 --', 'info')
        bl.addWidget(self.project_chip); bl.addWidget(add); bl.addWidget(refresh); bl.addStretch()
        self.layout.addWidget(bar)
        self.grid = QGridLayout(); self.grid.setSpacing(12); self.layout.addLayout(self.grid)
        self.cards=[]
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QFrame(); left.setProperty('card', True); ll=QVBoxLayout(left); ll.addWidget(title_label('项目组合视图', '按健康度、类型和阶段查看整体生产资源分布。'))
        self.type_chart = MiniBarChart('项目类型分布', [])
        self.health_chart = MiniBarChart('健康度排行', [])
        ll.addWidget(self.type_chart); ll.addWidget(self.health_chart)
        splitter.addWidget(left)
        right = QFrame(); right.setProperty('card', True); rl=QVBoxLayout(right); rl.addWidget(title_label('数据集交付台账', '表格仍保留，但作为交付台账：关注状态、版本、健康度和截止时间。'))
        self.table = QTableWidget(); rl.addWidget(self.table)
        splitter.addWidget(right); splitter.setSizes([450, 980])
        self.layout.addWidget(splitter, 1)

    def refresh(self):
        rows = list_projects()
        self.project_chip.setText(f'项目数 {len(rows)}')
        for c in self.cards: c.setParent(None)
        self.cards.clear()
        total_samples = sum(int(r.get('sample_count') or 0) for r in rows)
        avg_health = sum(float(r.get('health_score') or 0) for r in rows) / max(1,len(rows))
        active = sum(1 for r in rows if r.get('status') in ('生产中','质检中'))
        labels = sum(int(r.get('label_count') or 0) for r in rows)
        items=[('生产中项目', active, '需要持续导入、标注、质检', 'blue'),('样本总量', total_samples, '已入库训练样本规模', 'green'),('标签体系', labels, '跨项目标签定义数量', 'amber'),('平均健康度', f'{avg_health:.1f}', '用于判断可交付成熟度', 'blue')]
        for i,(t,v,d,tone) in enumerate(items):
            wc=WorkflowCard(t,str(v),d,t,tone); wc.clicked.connect(lambda x: QMessageBox.information(self,'项目态势',f'已选中指标：{x}'))
            self.grid.addWidget(wc,0,i); self.cards.append(wc)
        type_counts={}
        for r in rows: type_counts[r.get('project_type') or '未知']=type_counts.get(r.get('project_type') or '未知',0)+1
        self.type_chart.set_data(list(type_counts.items()), '项目类型分布', '')
        self.health_chart.set_data([(r['code'].replace('DS-',''), float(r.get('health_score') or 0)) for r in rows], '健康度排行', '分')
        enriched=[]
        for r in rows:
            m=dashboard_metrics(r['id'])
            enriched.append({**r, 'annotated_rate': f"{m.get('annotated_rate',0):.1f}%", 'rework_rate': f"{m.get('rework_rate',0)*100:.1f}%", 'delivery': '可交付' if m.get('health_score',0)>=90 else ('建议复核' if m.get('health_score',0)>=80 else '存在风险')})
        fill_table(self.table, enriched, [('code','项目编号'),('name','项目名称'),('project_type','项目类型'),('data_type','数据类型'),('sample_count','样本数'),('label_count','标签数'),('annotated_rate','标注完成'),('rework_rate','返工率'),('status','状态'),('version_no','版本'),('health_score','健康度'),('delivery','交付判断'),('deadline','截止时间')])

    def add_project(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('创建数据集项目')
        dlg.setObjectName('lightDialog')
        dlg.setMinimumWidth(520)
        dlg.setModal(True)

        form = QFormLayout(dlg)
        form.setContentsMargins(26, 22, 26, 20)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        header = QLabel('创建数据集项目')
        header.setProperty('dialogTitle', True)
        desc = QLabel('用于建立新的训练样本生产项目，创建后可继续配置标签体系、导入样本并生成任务包。')
        desc.setProperty('dialogDesc', True)
        desc.setWordWrap(True)
        form.addRow(header)
        form.addRow(desc)

        code = QLineEdit('DS-NEW-2026-003')
        name = QLineEdit('新增模型训练样本数据集')
        ptype = QComboBox(); ptype.addItems(['图像目标检测','图像分类','图像分割','文本分类','实体识别','问答样本评分','偏好数据标注','表格样本校验'])
        dtype = QComboBox(); dtype.addItems(['图像','文本','表格','多模态'])
        task = QLineEdit('智能预标注 + 人工修正 + 质量复核')
        goal = QLineEdit('用于训练行业场景识别模型')
        deadline = QDateEdit(QDate(2026, 8, 1)); deadline.setCalendarPopup(True); deadline.setDisplayFormat('yyyy-MM-dd')

        fields = [
            ('项目编号 *', code),
            ('项目名称 *', name),
            ('项目类型 *', ptype),
            ('数据类型 *', dtype),
            ('标注任务类型 *', task),
            ('模型训练目标 *', goal),
            ('截止时间 *', deadline),
        ]
        for label, widget in fields:
            widget.setMinimumHeight(38)
            form.addRow(label, widget)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        ok_btn.setText('创建项目')
        cancel_btn.setText('取消')
        cancel_btn.setProperty('secondary', True)
        form.addRow(buttons)

        def submit():
            required = [code.text().strip(), name.text().strip(), task.text().strip(), goal.text().strip()]
            if not all(required):
                QMessageBox.warning(dlg, '信息不完整', '请填写所有带 * 的必填字段。')
                return
            dlg.accept()

        buttons.accepted.connect(submit)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec():
            create_project({
                'code': code.text().strip(),
                'name': name.text().strip(),
                'project_type': ptype.currentText(),
                'data_type': dtype.currentText(),
                'task_type': task.text().strip(),
                'training_goal': goal.text().strip(),
                'deadline': deadline.date().toString('yyyy-MM-dd')
            }, self.user['username'])
            QMessageBox.information(self, '创建成功', '数据集项目已创建，并进入生产配置待完善状态。')
            self.refresh()
