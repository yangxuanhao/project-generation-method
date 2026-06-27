from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QSplitter, QFrame, QTabWidget, QTableWidget, QTextEdit, QMessageBox, QComboBox,
    QProgressBar, QInputDialog, QCheckBox, QGridLayout
)
from PyQt6.QtCore import Qt
from app.ui.utils import page_root, fill_table, secondary, danger, success, attach_page, title_label, pill
from app.widgets.image_canvas import ImageCanvas
from app.widgets.object_list_widget import ObjectListWidget
from app.widgets.visual_widgets import MiniBarChart, WorkflowCard, RiskHeatmap, ChecklistWidget
from app.services.dataset_service import list_projects, list_samples, get_labels, annotations_for_sample, list_rules
from app.services.prelabel_service import generate_prelabels_for_sample, accept_prelabels, create_bbox, delete_annotation
from app.services.quality_service import run_quality_check, submit_for_review
from app.core.database import fetch_all, fetch_one, execute, log_action


class AnnotationWorkbench(QWidget):
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.project_id = None
        self.sample_id = None
        self.labels = []
        root, self.layout = page_root('样本标注生产工作台', '五区联动：任务队列、专业画布、预标注修正、实时质检、提交门禁与返工说明。', show_header=False)
        attach_page(self, root)

        top = QFrame(); top.setProperty('card', True); top_l = QHBoxLayout(top); top_l.setContentsMargins(14, 10, 14, 10)
        self.project_combo = QComboBox(); self.project_combo.currentIndexChanged.connect(self.project_changed)
        self.task_info = QLabel('任务包：等待加载'); self.task_info.setStyleSheet('font-weight:900;color:#0f172a;')
        self.progress = QProgressBar(); self.progress.setFixedWidth(220)
        self.quality_chip = pill('质量分 --', 'info')
        top_l.addWidget(QLabel('项目')); top_l.addWidget(self.project_combo, 2); top_l.addWidget(self.task_info, 3); top_l.addWidget(self.quality_chip); top_l.addWidget(self.progress)
        save = success(QPushButton('保存并下一张')); save.clicked.connect(self.save_next)
        check = QPushButton('实时自检'); check.clicked.connect(self.self_check)
        submit = QPushButton('提交审核'); submit.clicked.connect(self.submit_review)
        skip = secondary(QPushButton('跳过并说明')); skip.clicked.connect(self.skip_with_reason)
        top_l.addWidget(save); top_l.addWidget(check); top_l.addWidget(submit); top_l.addWidget(skip)
        self.layout.addWidget(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QFrame(); left.setProperty('card', True); left.setMinimumWidth(280)
        left_l = QVBoxLayout(left); left_l.setContentsMargins(12, 12, 12, 12); left_l.setSpacing(10)
        left_l.addWidget(title_label('风险优先样本队列', '队列根据状态、返工、低置信、重复疑似和 Ground Truth 自动排序。'))
        filter_bar = QHBoxLayout(); self.filter_combo = QComboBox(); self.filter_combo.addItems(['全部','未标注','预标注待确认','质检异常','返工样本','低置信样本','疑难样本','重复疑似样本','Ground Truth'])
        self.filter_combo.currentIndexChanged.connect(self.refresh_samples)
        self.sort_combo = QComboBox(); self.sort_combo.addItems(['风险优先','任务顺序','返工次数','低置信优先'])
        self.sort_combo.currentIndexChanged.connect(self.refresh_samples)
        filter_bar.addWidget(self.filter_combo); filter_bar.addWidget(self.sort_combo); left_l.addLayout(filter_bar)
        self.sample_list = QListWidget(); self.sample_list.currentRowChanged.connect(self.sample_selected)
        left_l.addWidget(self.sample_list, 1)
        self.queue_heat = RiskHeatmap('队列风险构成', {})
        left_l.addWidget(self.queue_heat)
        splitter.addWidget(left)

        center = QFrame(); center.setProperty('workbenchPanel', True)
        center_l = QVBoxLayout(center); center_l.setContentsMargins(12, 12, 12, 12); center_l.setSpacing(8)
        tools = QHBoxLayout()
        self.draw_btn = QPushButton('矩形'); self.draw_btn.setCheckable(True); self.draw_btn.setChecked(True); self.draw_btn.clicked.connect(lambda: setattr(self.canvas, 'mode', 'draw'))
        fit = secondary(QPushButton('适窗')); fit.clicked.connect(lambda: (self.canvas.fit_to_window(), self.canvas.update()))
        raw = secondary(QPushButton('原图')); raw.clicked.connect(lambda: (setattr(self.canvas, 'zoom', 1.0), self.canvas.update()))
        gen = QPushButton('AI预标注'); gen.clicked.connect(self.run_prelabel)
        accept = QPushButton('全接受'); accept.clicked.connect(self.accept_all)
        delete = danger(QPushButton('删对象')); delete.clicked.connect(self.delete_selected)
        self.prelabel_layer = QCheckBox('预标注'); self.prelabel_layer.setChecked(True); self.prelabel_layer.stateChanged.connect(lambda _: (setattr(self.canvas,'show_prelabel',self.prelabel_layer.isChecked()), self.canvas.update()))
        self.quality_layer = QCheckBox('质检层'); self.quality_layer.setChecked(True); self.quality_layer.stateChanged.connect(lambda _: (setattr(self.canvas,'show_quality',self.quality_layer.isChecked()), self.canvas.update()))
        self.gt_layer = QCheckBox('GT层'); self.gt_layer.stateChanged.connect(lambda _: (setattr(self.canvas,'show_gt',self.gt_layer.isChecked()), self.canvas.update()))
        for w in [self.draw_btn, fit, raw, gen, accept, delete, self.prelabel_layer, self.quality_layer, self.gt_layer]: tools.addWidget(w)
        tools.addStretch(); center_l.addLayout(tools)
        self.canvas = ImageCanvas(); self.canvas.bbox_created.connect(self.create_box_from_canvas); self.canvas.bbox_selected.connect(self.object_clicked)
        center_l.addWidget(self.canvas, 1)
        status = QFrame(); status.setStyleSheet('QFrame{background:#111827;border-radius:12px;} QLabel{color:#cbd5e1;}')
        st_l=QHBoxLayout(status); st_l.setContentsMargins(10,6,10,6)
        self.bottom_status = QLabel('快捷键：1-person 2-helmet 3-no_helmet 4-vest｜当前耗时 00:00｜自动保存：等待操作')
        self.recent_hint = QLabel('最近提示：无')
        st_l.addWidget(self.bottom_status, 2); st_l.addWidget(self.recent_hint, 1)
        center_l.addWidget(status)
        splitter.addWidget(center)

        right = QFrame(); right.setProperty('card', True); right.setMinimumWidth(330)
        right_l = QVBoxLayout(right); right_l.setContentsMargins(10, 10, 10, 10)
        self.right_tabs = QTabWidget()
        label_tab = QWidget(); label_l = QVBoxLayout(label_tab); label_l.addWidget(title_label('标签与规范', '点击标签后，画布拖拽即可新增对象。'))
        self.label_buttons_frame = QVBoxLayout(); label_l.addLayout(self.label_buttons_frame); label_l.addStretch()
        self.object_table = ObjectListWidget(); self.object_table.object_selected.connect(self.object_clicked)
        issue_tab = QWidget(); issue_l = QVBoxLayout(issue_tab)
        self.issue_chart = MiniBarChart('问题严重度', [])
        self.issue_table = QTableWidget()
        issue_l.addWidget(self.issue_chart); issue_l.addWidget(self.issue_table)
        gate_tab = QWidget(); gate_l = QVBoxLayout(gate_tab); gate_l.addWidget(title_label('提交门禁', '提交审核前必须通过以下阻断项。'))
        self.gate = ChecklistWidget([]); gate_l.addWidget(self.gate)
        self.rule_text = QTextEdit(); self.rule_text.setReadOnly(True)
        self.rework_text = QTextEdit(); self.rework_text.setPlaceholderText('返工模式下显示质检退回原因、问题位置、截止时间和二次提交要求。')
        ai_tab = QWidget(); ai_l = QVBoxLayout(ai_tab); ai_l.addWidget(title_label('AI 助手建议', '聚合预标注置信度、历史返工和质检问题生成操作建议。'))
        self.ai_suggestions = QTextEdit(); self.ai_suggestions.setReadOnly(True); ai_l.addWidget(self.ai_suggestions)
        difficult_tab = QWidget(); d_l = QVBoxLayout(difficult_tab)
        self.difficult_type = QComboBox(); self.difficult_type.addItems(['目标过小','目标遮挡','图片模糊','类别不确定','标签体系缺失','规范不明确','需要质检员判断','建议新增标签'])
        self.difficult_note = QTextEdit(); self.difficult_note.setPlaceholderText('请填写疑难说明，提交后进入疑难池。')
        mark = QPushButton('标记疑难并进入仲裁池'); mark.clicked.connect(self.mark_difficult)
        d_l.addWidget(QLabel('疑难类型')); d_l.addWidget(self.difficult_type); d_l.addWidget(self.difficult_note); d_l.addWidget(mark)
        self.right_tabs.addTab(label_tab, '标签')
        self.right_tabs.addTab(self.object_table, '对象')
        self.right_tabs.addTab(issue_tab, '实时质检')
        self.right_tabs.addTab(gate_tab, '提交门禁')
        self.right_tabs.addTab(ai_tab, 'AI建议')
        self.right_tabs.addTab(self.rework_text, '返工')
        self.right_tabs.addTab(self.rule_text, '规范')
        self.right_tabs.addTab(difficult_tab, '疑难')
        right_l.addWidget(self.right_tabs)
        splitter.addWidget(right)
        splitter.setSizes([300, 540, 340])
        self.layout.addWidget(splitter, 1)

    def refresh(self):
        current = self.project_combo.currentData()
        self.project_combo.blockSignals(True); self.project_combo.clear()
        for p in list_projects():
            if p['data_type'] == '图像': self.project_combo.addItem(f"{p['code']}｜{p['name']}", p['id'])
        if current:
            idx = self.project_combo.findData(current)
            if idx >= 0: self.project_combo.setCurrentIndex(idx)
        self.project_combo.blockSignals(False)
        self.project_changed()

    def project_changed(self):
        self.project_id = self.project_combo.currentData()
        self.labels = get_labels(self.project_id) if self.project_id else []
        self.build_label_buttons(); self.refresh_samples()
        rules = list_rules(self.project_id) if self.project_id else []
        self.rule_text.setText('\n\n'.join([f"【{r['severity']}】{r['title']}\n{r['content']}" for r in rules]))

    def build_label_buttons(self):
        while self.label_buttons_frame.count():
            item = self.label_buttons_frame.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for lab in self.labels:
            btn = QPushButton(f"{lab['shortcut']}  {lab['name']}｜{lab['description'][:22]}")
            btn.setStyleSheet(f"background:{lab['color']};color:white;text-align:left;border-radius:12px;padding:10px;font-weight:800;")
            btn.setToolTip(f"正例：{lab.get('positive_example','')}\n反例：{lab.get('negative_example','')}\n注意：{lab.get('note','')}")
            btn.clicked.connect(lambda _, n=lab['name']: self.set_label(n))
            self.label_buttons_frame.addWidget(btn)

    def set_label(self, label: str):
        self.canvas.set_current_label(label)
        self.bottom_status.setText(f'当前绘制标签：{label}｜在画布拖拽新增目标框｜快捷键已同步')

    def risk_score(self, s: dict) -> int:
        score = 0
        score += 30 if '异常' in s.get('status','') or s.get('qc_status') == '待质检' else 0
        score += int(s.get('rework_count') or 0) * 18
        score += 20 if s.get('is_low_confidence') else 0
        score += 15 if s.get('is_duplicate') else 0
        score += 10 if s.get('is_ground_truth') else 0
        score += 10 if '模糊' in (s.get('risk_tags') or '') else 0
        return score

    def refresh_samples(self):
        self.sample_list.clear()
        if not self.project_id: return
        rows = list_samples(self.project_id, 'image')
        f = self.filter_combo.currentText()
        def keep(s):
            if f == '全部': return True
            if f == '未标注': return s['status'] == '未开始'
            if f == '预标注待确认': return '预标注' in s['status']
            if f == '质检异常': return '异常' in s['status'] or s['qc_status'] == '待质检'
            if f == '返工样本': return s['rework_count'] > 0 or '返工' in s['status']
            if f == '低置信样本': return s['is_low_confidence'] == 1
            if f == '疑难样本': return '疑难' in s['status'] or '疑难' in (s.get('risk_tags') or '')
            if f == '重复疑似样本': return s['is_duplicate'] == 1
            if f == 'Ground Truth': return s['is_ground_truth'] == 1
            return True
        self.samples = [s for s in rows if keep(s)]
        sort = self.sort_combo.currentText()
        if sort == '风险优先': self.samples.sort(key=self.risk_score, reverse=True)
        elif sort == '返工次数': self.samples.sort(key=lambda s: s.get('rework_count') or 0, reverse=True)
        elif sort == '低置信优先': self.samples.sort(key=lambda s: s.get('is_low_confidence') or 0, reverse=True)
        for s in self.samples:
            risk = self.risk_score(s)
            prefix = '🔥' if risk >= 45 else ('⚠' if risk >= 25 else '✓')
            item = QListWidgetItem(f"{prefix} {s['sample_code']}｜{s['filename']}\n状态:{s['status']}｜质检:{s['qc_status']}｜风险:{s['risk_tags'] or '无'}｜返工:{s['rework_count']}｜GT:{'是' if s['is_ground_truth'] else '否'}")
            item.setData(Qt.ItemDataRole.UserRole, s['id'])
            item.setToolTip(f"风险分：{risk}\n点击加载到中央画布")
            self.sample_list.addItem(item)
        total = max(1, len(rows)); done = sum(1 for s in rows if s['status'] in ('已保存','已提交','已通过'))
        self.progress.setValue(int(done/total*100))
        risk_data = {
            '待确认预标注': sum(1 for s in rows if '预标注' in s['status']),
            '返工样本': sum(1 for s in rows if s['rework_count'] > 0),
            '低置信': sum(1 for s in rows if s['is_low_confidence']),
            '重复疑似': sum(1 for s in rows if s['is_duplicate']),
            '待质检': sum(1 for s in rows if s['qc_status'] == '待质检'),
            'Ground Truth': sum(1 for s in rows if s['is_ground_truth']),
        }
        self.queue_heat.set_data(risk_data)
        if self.samples and self.sample_list.currentRow() < 0: self.sample_list.setCurrentRow(0)

    def sample_selected(self, row: int):
        if row < 0 or row >= len(getattr(self, 'samples', [])): return
        s = self.samples[row]; self.sample_id = s['id']
        quality = max(0, 100 - self.risk_score(s))
        self.quality_chip.setText(f'质量分 {quality}')
        tone = 'success' if quality >= 80 else ('warn' if quality >= 60 else 'danger')
        self.quality_chip.setProperty('pill', tone); self.quality_chip.style().unpolish(self.quality_chip); self.quality_chip.style().polish(self.quality_chip)
        self.task_info.setText(f"任务包 TB-IMG-202606｜样本 {s['sample_code']}｜{s['status']}｜{s['qc_status']}")
        self.reload_current_sample()

    def reload_current_sample(self):
        if not self.sample_id: return
        s = fetch_one('SELECT * FROM samples WHERE id=?', (self.sample_id,))
        if not s: return
        anns = annotations_for_sample(self.sample_id)
        color_map = {l['name']: l['color'] for l in self.labels}
        issue_rows = fetch_all("SELECT * FROM quality_issues WHERE sample_id=? AND status!='已关闭'", (self.sample_id,))
        issue_ann_ids = {i['annotation_id'] for i in issue_rows if i.get('annotation_id')}
        for a in anns:
            a['color'] = color_map.get(a['label'], '#22c55e')
            if a['id'] in issue_ann_ids: a['issue'] = True
        self.canvas.load_image(s['file_path'], anns)
        self.object_table.set_objects(anns)
        fill_table(self.issue_table, issue_rows, [('issue_type','问题'),('severity','严重'),('rule_name','规则'),('position_text','位置'),('suggestion','建议'),('status','状态')])
        counter = {'高': 0, '中': 0, '低': 0}
        for i in issue_rows: counter[i.get('severity','中')] = counter.get(i.get('severity','中'), 0) + 1
        self.issue_chart.set_data(list(counter.items()), '问题严重度', '')
        unconfirmed = sum(1 for a in anns if a.get('source') == '预标注' and a.get('status') == '待确认')
        blockers = [
            ('预标注全部确认', unconfirmed == 0, f'剩余 {unconfirmed} 个待确认候选'),
            ('无中高风险质检问题', not any(i['severity'] in ('高','中') for i in issue_rows), f'打开问题 {len(issue_rows)} 条'),
            ('对象数量合理', len(anns) > 0, f'当前对象 {len(anns)} 个'),
            ('返工意见已处理', not ('返工' in s.get('status','') and len(issue_rows) > 0), '返工样本需二次自检'),
            ('疑难说明完整', '疑难' not in s.get('status',''), '疑难样本必须填写说明'),
        ]
        self.gate.set_items(blockers)
        reworks = fetch_all('SELECT * FROM rework_tasks WHERE sample_id=? ORDER BY id DESC', (self.sample_id,))
        if reworks:
            rw = reworks[0]
            self.rework_text.setText(f"返工单：{rw['rework_code']}\n状态：{rw['status']}\n截止：{rw['deadline']}\n退回原因：{rw['issue_desc']}\n返工要求：{rw['requirement']}\n二检结果：{rw.get('second_review','') or '待二检'}")
        else:
            self.rework_text.setText('当前样本未处于返工模式。')
        suggestions = []
        if unconfirmed: suggestions.append(f'有 {unconfirmed} 个预标注候选未确认，建议逐个接受/修改/删除。')
        if s.get('is_low_confidence'): suggestions.append('该样本被标记为低置信，建议放大检查小目标与类别边界。')
        if s.get('is_duplicate'): suggestions.append('该样本疑似重复，建议与导入体检结果比对后决定是否保留。')
        if issue_rows: suggestions.append('存在打开的自动质检问题，请先定位问题框并修复后再提交。')
        if not suggestions: suggestions.append('当前样本风险较低，可保存并继续下一张。')
        self.ai_suggestions.setText('\n'.join(f'• {x}' for x in suggestions))
        self.bottom_status.setText(f"快捷键：1-person 2-helmet 3-no_helmet 4-vest｜对象 {len(anns)}｜自动保存：已加载 {s['sample_code']}")
        self.recent_hint.setText(f"最近提示：{issue_rows[0]['issue_type'] if issue_rows else '无'}")

    def run_prelabel(self):
        if not self.sample_id: return
        n = generate_prelabels_for_sample(self.sample_id, self.user['username'])
        QMessageBox.information(self, '智能预标注完成', f'模型候选框已生成 {n} 个。请在画布中接受、修改或删除。')
        self.reload_current_sample()

    def accept_all(self):
        if not self.sample_id: return
        n = accept_prelabels(self.sample_id, self.user['username'])
        QMessageBox.information(self, '预标注已确认', f'已接受 {n} 个预标注对象，系统将统计预标注采用率。')
        self.reload_current_sample()

    def create_box_from_canvas(self, box: dict):
        if not self.sample_id: return
        create_bbox(self.sample_id, box['label'], box['x'], box['y'], box['w'], box['h'], self.user['username'])
        self.reload_current_sample()

    def object_clicked(self, annotation_id: int):
        self.canvas.select_box(annotation_id)

    def delete_selected(self):
        aid = self.canvas.selected_id
        if not aid:
            QMessageBox.warning(self, '未选择对象', '请先在画布或对象列表中选择一个标注对象。')
            return
        reason, ok = QInputDialog.getItem(self, '删除原因', '请选择删除预标注/标注的原因', ['误检','类别错误','位置不准','目标不存在','目标过小','目标模糊','与其他框重复'], 0, False)
        if ok:
            delete_annotation(aid, self.user['username'], reason)
            self.reload_current_sample()

    def self_check(self):
        if not self.sample_id: return
        issues = run_quality_check(self.sample_id, self.user['username'])
        QMessageBox.information(self, '自动自检完成', f'本样本检出 {len(issues)} 个问题。严重问题会在画布和右侧质检面板中高亮。')
        self.reload_current_sample()

    def submit_review(self):
        if not self.project_id: return
        ids = [s['id'] for s in list_samples(self.project_id, 'image') if s.get('assigned_to') == self.user['username'] or self.user['role'] == '管理员']
        ok, msg = submit_for_review(ids[:8], self.user['username'])
        QMessageBox.information(self, '提交前强制检查', msg)
        self.refresh_samples()

    def save_next(self):
        if not self.sample_id: return
        execute("UPDATE samples SET status='已保存' WHERE id=?", (self.sample_id,))
        log_action(self.user['username'], '保存并下一张', f"样本{self.sample_id}")
        row = self.sample_list.currentRow()
        if row + 1 < self.sample_list.count(): self.sample_list.setCurrentRow(row + 1)
        else: QMessageBox.information(self, '任务包完成', '当前筛选队列已处理完，可执行提交审核。')
        self.refresh_samples()

    def skip_with_reason(self):
        if not self.sample_id: return
        reason, ok = QInputDialog.getText(self, '跳过说明', '请说明跳过原因（疑难、图片不可读、等待仲裁等）')
        if ok and reason.strip():
            execute("UPDATE samples SET status='疑难待仲裁', risk_tags=risk_tags||? WHERE id=?", (';跳过:'+reason.strip(), self.sample_id))
            log_action(self.user['username'], '跳过样本', f"样本{self.sample_id} {reason}")
            QMessageBox.information(self, '已跳过并记录', '样本已进入疑难/待仲裁队列。')
            self.refresh_samples()

    def mark_difficult(self):
        if not self.sample_id: return
        note = self.difficult_note.toPlainText().strip()
        if len(note) < 5:
            QMessageBox.warning(self, '说明不足', '请填写更具体的疑难说明。')
            return
        execute("UPDATE samples SET status='疑难待仲裁', risk_tags=risk_tags||? WHERE id=?", (';疑难:'+self.difficult_type.currentText(), self.sample_id))
        log_action(self.user['username'], '标记疑难样本', f"样本{self.sample_id} {self.difficult_type.currentText()} {note}")
        QMessageBox.information(self, '已进入疑难池', '该样本已标记为疑难，等待质检员或管理员仲裁。')
        self.refresh_samples()
