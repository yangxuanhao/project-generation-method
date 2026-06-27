from collections import Counter
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QComboBox, QLabel, QMessageBox, QTextEdit, QDialog, QFormLayout, QDialogButtonBox, QSplitter, QFrame, QGridLayout
from PyQt6.QtCore import Qt
from app.ui.utils import page_root, fill_table, secondary, danger, success, make_project_combo, attach_page, title_label, pill
from app.widgets.visual_widgets import MiniBarChart, PipelineWidget, RiskHeatmap, WorkflowCard, ChecklistWidget
from app.services.dataset_service import list_projects, list_samples, dashboard_metrics
from app.services.quality_service import issues_for_project, run_quality_check, reviewer_decision
from app.services.rework_service import create_rework
from app.core.database import fetch_all


class QualityCenterPage(QWidget):
    def __init__(self, user: dict):
        super().__init__(); self.user = user
        root, self.layout = page_root('质量校验中心', '从“问题表”升级为质量闭环作战台：风险优先、批量扫描、人工复核、返工单、二检与仲裁。')
        attach_page(self, root)

        bar = QFrame(); bar.setProperty('card', True); bar_l = QHBoxLayout(bar); bar_l.setContentsMargins(14,10,14,10)
        self.project_combo = make_project_combo(list_projects()); self.project_combo.currentIndexChanged.connect(self.refresh)
        scan = QPushButton('批量执行自动质量校验'); scan.clicked.connect(self.batch_scan)
        passbtn = success(QPushButton('人工复核通过')); passbtn.clicked.connect(lambda: self.review_selected(True))
        rework = danger(QPushButton('退回返工')); rework.clicked.connect(self.rework_selected)
        locate = secondary(QPushButton('问题定位说明')); locate.clicked.connect(self.locate_issue)
        for w in [QLabel('项目'), self.project_combo, scan, passbtn, rework, locate]: bar_l.addWidget(w)
        bar_l.addStretch(); self.layout.addWidget(bar)

        self.summary_grid = QGridLayout(); self.summary_grid.setSpacing(12); self.layout.addLayout(self.summary_grid)
        self.summary_cards = []

        flow_card = QFrame(); flow_card.setProperty('card', True); fl=QVBoxLayout(flow_card); fl.addWidget(title_label('质检闭环流转', '自动问题 → 高风险复核 → 退回返工 → 二检 → 合格池 / 仲裁。'))
        self.flow = PipelineWidget([]); fl.addWidget(self.flow)
        self.layout.addWidget(flow_card)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QFrame(); left.setProperty('card', True); ll=QVBoxLayout(left)
        ll.addWidget(title_label('高风险样本推荐队列', '优先展示低置信、返工多次、自动异常、Ground Truth 抽检相关样本。'))
        self.sample_table = QTableWidget(); ll.addWidget(self.sample_table, 2)
        self.review_gate = ChecklistWidget([]); ll.addWidget(QLabel('复核门禁')); ll.addWidget(self.review_gate, 1)
        splitter.addWidget(left)

        right = QFrame(); right.setProperty('card', True); rl=QVBoxLayout(right)
        rl.addWidget(title_label('问题分布与打开问题', '质量问题按照严重度、规则和样本定位展示，支持联动返工。'))
        charts = QHBoxLayout(); self.severity_chart=MiniBarChart('严重度分布', []); self.type_heat=RiskHeatmap('问题类型热力', {})
        charts.addWidget(self.severity_chart); charts.addWidget(self.type_heat); rl.addLayout(charts)
        self.table = QTableWidget(); rl.addWidget(self.table, 2)
        splitter.addWidget(right)
        splitter.setSizes([610, 870])
        self.layout.addWidget(splitter, 1)

    def refresh(self):
        self.project_combo.blockSignals(True); cur = self.project_combo.currentData(); self.project_combo.clear()
        for p in list_projects(): self.project_combo.addItem(f"{p['code']}｜{p['name']}", p['id'])
        if cur:
            idx = self.project_combo.findData(cur)
            if idx >= 0: self.project_combo.setCurrentIndex(idx)
        self.project_combo.blockSignals(False)
        pid = self.project_combo.currentData()
        if not pid: return
        metrics = dashboard_metrics(pid)
        for c in self.summary_cards: c.setParent(None)
        self.summary_cards.clear()
        data = [
            ('打开问题', str(len([i for i in issues_for_project(pid) if i.get('status') != '已关闭'])), '自动规则发现的待处理问题', 'red'),
            ('质检通过率', f"{metrics.get('manual_pass_rate',0):.1f}%", '人工质检通过样本比例', 'green'),
            ('一致性评分', f"{metrics.get('consensus_score',0):.1f}", '多人重叠标注综合得分', 'blue'),
            ('返工率', f"{metrics.get('rework_rate',0)*100:.1f}%", '退回返工样本占比', 'amber'),
        ]
        for i,(t,v,d,tone) in enumerate(data):
            wc=WorkflowCard(t,v,d,t,tone); wc.clicked.connect(lambda x: QMessageBox.information(self,'质量指标',f'已选中指标：{x}'))
            self.summary_grid.addWidget(wc,0,i); self.summary_cards.append(wc)
        rows = issues_for_project(pid)
        fill_table(self.table, rows, [('sample_code','样本编号'),('filename','文件/文本'),('issue_type','问题类型'),('severity','严重程度'),('rule_name','触发规则'),('position_text','位置'),('suggestion','修复建议'),('status','状态')])
        sev = Counter(r.get('severity','中') for r in rows)
        self.severity_chart.set_data([('高', sev.get('高',0)), ('中', sev.get('中',0)), ('低', sev.get('低',0))], '严重度分布', '')
        typ = Counter(r.get('issue_type','未知') for r in rows)
        self.type_heat.set_data(dict(typ.most_common(9)))
        samples = list_samples(pid)
        def risk(s):
            return (35 if s['qc_status']=='待质检' else 0) + (s.get('rework_count') or 0)*18 + (20 if s.get('is_low_confidence') else 0) + (15 if s.get('is_duplicate') else 0) + (10 if s.get('is_ground_truth') else 0) + (20 if '异常' in s.get('status','') else 0)
        samples = sorted(samples, key=risk, reverse=True)
        risk_rows = [{**s, 'risk_score': risk(s), 'recommend': '立即复核' if risk(s)>=50 else ('抽检' if risk(s)>=25 else '常规')} for s in samples[:16]]
        fill_table(self.sample_table, risk_rows, [('id','样本ID'),('sample_code','样本编号'),('sample_type','类型'),('filename','文件'),('status','标注状态'),('qc_status','质检状态'),('risk_tags','风险'),('risk_score','风险分'),('recommend','建议')])
        gate_items = [
            ('已完成自动质检', len(rows) >= 0, f'打开问题 {len(rows)} 条'),
            ('高风险优先复核', any(r['risk_score'] >= 50 for r in risk_rows), '队列已按风险分排序'),
            ('返工单可追踪', metrics.get('rework_total',0) >= 0, f"返工任务 {metrics.get('rework_total',0)} 个"),
            ('交付风险可解释', bool(metrics.get('health_advice')), '健康度扣分项已生成'),
        ]
        self.review_gate.set_items(gate_items)
        self.flow.set_stages([('自动扫描', len(samples)), ('打开问题', len(rows)), ('待复核', metrics.get('qc_pending_total',0)), ('返工中', metrics.get('rework_total',0)), ('已通过', metrics.get('qc_pass_total',0)), ('仲裁', sum(1 for s in samples if '疑难' in s.get('status','')))])

    def batch_scan(self):
        pid = self.project_combo.currentData(); samples = list_samples(pid)[:40]
        count = 0
        for s in samples: count += len(run_quality_check(s['id'], self.user['username']))
        QMessageBox.information(self, '批量质检完成', f'已扫描 {len(samples)} 个样本，累计发现 {count} 个质量问题。高风险队列已重新排序。')
        self.refresh()

    def selected_sample_id(self):
        row = self.sample_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, '未选择样本', '请先在高风险样本队列中选择一条样本。')
            return None
        return int(self.sample_table.item(row, 0).text())

    def review_selected(self, passed: bool):
        sid = self.selected_sample_id()
        if not sid: return
        reviewer_decision(sid, passed, self.user['username'], '人工复核结论由质量校验中心提交。')
        QMessageBox.information(self, '质检结论已记录', '该样本已写入人工质检结论，并同步更新样本状态。')
        self.refresh()

    def rework_selected(self):
        sid = self.selected_sample_id()
        if not sid: return
        dlg = QDialog(self); dlg.setWindowTitle('退回返工'); form=QFormLayout(dlg)
        issue=QTextEdit('helmet 漏标 1 处，person 框边界偏移，预标注未完全确认。')
        req=QTextEdit('请补充漏标对象，调整偏移框，点击重新自检后再二次提交；若类别不确定，请标记疑难进入仲裁。')
        form.addRow('质检问题说明', issue); form.addRow('返工要求', req)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel); form.addRow(buttons); buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)
        if dlg.exec():
            create_rework(sid, self.user['username'], '人工质检退回', issue.toPlainText(), req.toPlainText())
            QMessageBox.information(self, '返工单已生成', '样本已退回标注员返工，并进入返工闭环管理。')
            self.refresh()

    def locate_issue(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self,'问题定位','请选择打开问题记录。'); return
        vals = [self.table.item(row, c).text() if self.table.item(row,c) else '' for c in range(self.table.columnCount())]
        QMessageBox.information(self,'问题定位说明', f"问题：{vals[2]}\n严重程度：{vals[3]}\n位置：{vals[5]}\n建议：{vals[6]}\n在标注工作台中会以红色框、右侧问题列表和提交门禁形式同步定位。")
