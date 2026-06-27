from collections import Counter
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QTableWidget, QHBoxLayout, QPushButton, QMessageBox, QFrame, QSplitter, QComboBox
from PyQt6.QtCore import Qt
from app.ui.utils import page_root, card, fill_table, secondary, attach_page, title_label, pill
from app.widgets.metric_card import MetricCard
from app.widgets.visual_widgets import DonutGauge, MiniBarChart, PipelineWidget, TrendLine, WorkflowCard, RiskHeatmap
from app.services.dataset_service import dashboard_metrics, list_projects, update_project_health
from app.core.database import fetch_all


class DashboardPage(QWidget):
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        root, self.layout = page_root('数据集驾驶舱', '把样本生产、质量风险、返工闭环和版本交付放在同一个指挥视角，不再是普通统计表。')
        attach_page(self, root)

        hero = QFrame(); hero.setProperty('hero', True)
        hero_l = QHBoxLayout(hero); hero_l.setContentsMargins(22, 18, 22, 18); hero_l.setSpacing(18)
        left = QVBoxLayout(); left.setSpacing(8)
        self.project_label = QLabel(''); self.project_label.setStyleSheet('font-size:19px;font-weight:900;color:white;')
        self.project_goal = QLabel(''); self.project_goal.setStyleSheet('color:#dbeafe;'); self.project_goal.setWordWrap(True)
        chips = QHBoxLayout(); self.status_chip = pill('生产中', 'info'); self.role_chip = pill(f"当前用户：{user['display_name']} / {user['role']}", 'success'); chips.addWidget(self.status_chip); chips.addWidget(self.role_chip); chips.addStretch()
        left.addWidget(self.project_label); left.addWidget(self.project_goal); left.addLayout(chips)
        action = QHBoxLayout();
        self.project_combo = QComboBox(); self.project_combo.currentIndexChanged.connect(self.refresh)
        refresh = QPushButton('重算健康度'); refresh.clicked.connect(self.recompute_health)
        simulate = secondary(QPushButton('模拟今日质检扫描')); simulate.clicked.connect(self.simulate_scan)
        action.addWidget(QLabel('演示项目')); action.addWidget(self.project_combo, 1); action.addWidget(refresh); action.addWidget(simulate); action.addStretch(); left.addLayout(action)
        hero_l.addLayout(left, 2)
        self.gauge = DonutGauge('数据集健康度', 0, '分'); hero_l.addWidget(self.gauge)
        self.trend = TrendLine('近 7 批次质量走势', []); self.trend.setStyleSheet('background:transparent;'); hero_l.addWidget(self.trend, 2)
        self.layout.addWidget(hero)

        self.pipeline = PipelineWidget([]); pcard = card(); pl=QVBoxLayout(pcard); pl.addWidget(title_label('生产流程管线', '点击任一阶段可查看对应业务入口提示。')); pl.addWidget(self.pipeline)
        self.pipeline.stageClicked.connect(self.pipeline_clicked)
        self.layout.addWidget(pcard)

        self.grid = QGridLayout(); self.grid.setSpacing(12); self.layout.addLayout(self.grid)
        self.cards = []

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_panel = card(); lp=QVBoxLayout(left_panel); lp.addWidget(title_label('标签分布与长尾风险', '柱状图可点击，突出少数类、过载类和标签均衡度问题。'))
        self.label_chart = MiniBarChart('标签分布', [])
        self.label_chart.barClicked.connect(lambda k: QMessageBox.information(self, '标签联动', f'已选中标签「{k}」，可在工作台队列中按标签筛选相关样本。'))
        lp.addWidget(self.label_chart); self.label_table = QTableWidget(); lp.addWidget(self.label_table)
        splitter.addWidget(left_panel)

        right_panel = card(); rp=QVBoxLayout(right_panel); rp.addWidget(title_label('风险热力图与交付建议', '将自动质检、返工、重复、低置信和 Ground Truth 风险合并展示。'))
        self.risk_heat = RiskHeatmap('风险热力图', {})
        self.risk_heat.cellClicked.connect(lambda k: QMessageBox.information(self, '风险定位', f'已定位风险「{k}」，建议进入质量校验中心或返工闭环处理。'))
        rp.addWidget(self.risk_heat)
        self.issue_table = QTableWidget(); rp.addWidget(self.issue_table)
        splitter.addWidget(right_panel)
        splitter.setSizes([760, 720])
        self.layout.addWidget(splitter, 1)

    def refresh(self):
        projects = list_projects()
        current = self.project_combo.currentData() if hasattr(self, 'project_combo') else None
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for p in projects:
            self.project_combo.addItem(f"{p['code']}｜{p['name']}", p['id'])
        if current:
            idx = self.project_combo.findData(current)
            if idx >= 0: self.project_combo.setCurrentIndex(idx)
        self.project_combo.blockSignals(False)
        pid = self.project_combo.currentData() if projects else None
        project = next((p for p in projects if p['id'] == pid), projects[0] if projects else None)
        m = dashboard_metrics(pid)
        if not project or not m: return
        self.project_label.setText(f"{project['code']}｜{m.get('project_name','--')}")
        self.project_goal.setText(f"训练目标：{project.get('training_goal','--')}｜版本：{project.get('version_no','--')}｜截止：{project.get('deadline','--')}")
        health = float(m.get('health_score', 0)); self.gauge.set_value(health)
        self.status_chip.setText(project.get('status', '生产中'))
        self.status_chip.setProperty('pill', 'success' if health >= 90 else ('warn' if health >= 80 else 'danger'))
        self.status_chip.style().unpolish(self.status_chip); self.status_chip.style().polish(self.status_chip)
        for c in self.cards: c.setParent(None)
        self.cards.clear()
        items = [
            ('样本入库', m.get('sample_total',0), '图像/文本已完成体检入库', '数据体检'),
            ('标注完成率', f"{m.get('annotated_rate',0):.1f}%", '进入工作台继续处理未完成样本', '标注任务'),
            ('待质检', m.get('qc_pending_total',0), '优先由质检员处理高风险样本', '质量校验'),
            ('返工闭环', m.get('rework_total',0), '退回、二检、仲裁的闭环任务', '返工'),
            ('预标注采用率', f"{m.get('prelabel_adopt_rate',0)}%", '衡量模型辅助标注有效性', '智能预标注'),
            ('一致性评分', f"{m.get('consensus_score',0):.1f}", '多人重叠标注 / 文本标签一致', '一致性'),
            ('GT 抽检得分', f"{m.get('gt_score',0):.1f}", '隐藏标准答案质量检测', 'Ground Truth'),
            ('可交付版本', m.get('version_total',0), '冻结、导出、回滚记录', '版本交付'),
        ]
        for i, (t, v, s, key) in enumerate(items):
            cardw = WorkflowCard(t, str(v), s, key, ['blue','green','amber','red'][i % 4]); cardw.clicked.connect(self.card_clicked)
            self.grid.addWidget(cardw, i//4, i%4); self.cards.append(cardw)
        total = max(1, m.get('sample_total', 0))
        stages = [
            ('入库', m.get('sample_total',0)), ('已标注', m.get('annotated_total',0)), ('待质检', m.get('qc_pending_total',0)),
            ('返工', m.get('rework_total',0)), ('通过', m.get('qc_pass_total',0)), ('版本', m.get('version_total',0)),
        ]
        self.pipeline.set_stages(stages)
        labels = sorted(m.get('label_counts',{}).items(), key=lambda x: x[1], reverse=True)
        self.label_chart.set_data(labels, '标签分布：对象数量', '')
        labels_rows = [{'label': k, 'count': v, 'ratio': f"{v/max(1,sum(m.get('label_counts',{}).values())):.1%}", 'risk': '长尾' if v < max(2, sum(m.get('label_counts',{}).values())/max(1,len(m.get('label_counts',{})))*0.45) else '正常'} for k,v in labels]
        fill_table(self.label_table, labels_rows, [('label','标签'), ('count','数量'), ('ratio','占比'), ('risk','分布风险')])
        issues = fetch_all("""SELECT issue_type, severity, COUNT(*) c FROM quality_issues qi JOIN samples s ON qi.sample_id=s.id
                              WHERE s.project_id=? AND qi.status!='已关闭' GROUP BY issue_type,severity ORDER BY c DESC""", (pid,))
        risk_data = {r['issue_type']: int(r['c']) for r in issues}
        if not risk_data:
            risk_data = {'低置信样本': m.get('low_quality_total',0), '重复样本': int(m.get('duplicate_rate',0)*total), '返工样本': m.get('rework_total',0), '待质检': m.get('qc_pending_total',0)}
        self.risk_heat.set_data(risk_data)
        advice = [{'advice': x, 'status': '待处理' if '建议' in x or '不建议' in x or '偏低' in x else '观察'} for x in (m.get('health_advice') or ['当前暂无明显扣分项，可继续交付检查。'])]
        fill_table(self.issue_table, advice, [('advice','扣分项 / 优化建议'), ('status','处理状态')])
        trend = [('批次1', 76), ('批次2', 80), ('批次3', 83), ('批次4', 82), ('批次5', 86), ('当前', health)]
        self.trend.set_data(trend, '近 7 批次质量走势', '分')

    def card_clicked(self, key: str):
        QMessageBox.information(self, '业务入口联动', f'已聚焦「{key}」：真实系统中会自动带入筛选条件并跳转到对应队列。当前演示可通过左侧菜单进入明细页面。')

    def pipeline_clicked(self, stage: str):
        QMessageBox.information(self, '流程管线定位', f'已选择流程阶段：{stage}\n建议查看对应样本队列、质检中心或版本交付页面。')

    def simulate_scan(self):
        QMessageBox.information(self, '今日质检扫描', '已模拟完成：新增 2 条中风险提示，推荐优先处理低置信、重复疑似和返工超期样本。')

    def recompute_health(self):
        projects = list_projects()
        if projects:
            score = update_project_health(self.project_combo.currentData() or projects[0]['id'])
            QMessageBox.information(self, '健康度已更新', f'数据集健康度重新计算完成：{score} 分。')
            self.refresh()
