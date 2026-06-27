from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QTextEdit, QComboBox, QTableWidget, QSplitter, QFrame, QMessageBox, QSpinBox,
    QCheckBox, QTabWidget, QGridLayout, QGroupBox
)
from PyQt6.QtCore import Qt
from app.ui.utils import page_root, fill_table, secondary, pill
from app.services.dataset_service import list_projects, list_samples, get_labels, annotations_for_sample
from app.services.quality_service import run_quality_check
from app.core.database import execute, fetch_all, fetch_one, log_action


class TextAnnotationPage(QWidget):
    """高信息密度文本标注工作台。

    设计目标：减少中间大面积空白，把文本分类、实体标注、LLM偏好评价、
    质量问题和提交门禁放在同一屏内，便于真实生产作业连续处理。
    """

    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.project_id = None
        self.sample_id = None
        self.samples = []
        root, self.layout = page_root('文本标注工作台')
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(root)

        self._build_top_bar()
        self._build_metric_strip()
        self._build_work_area()

    def _build_top_bar(self):
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self.project_changed)
        self.project_combo.setMinimumWidth(420)

        self.save_btn = QPushButton('保存')
        self.save_btn.clicked.connect(self.save_text_annotation)
        self.check_btn = QPushButton('自检')
        self.check_btn.clicked.connect(self.self_check)
        self.pref_btn = secondary(QPushButton('AI评分建议'))
        self.pref_btn.clicked.connect(self.make_llm_eval)
        self.next_btn = secondary(QPushButton('保存并下一条'))
        self.next_btn.clicked.connect(self.save_and_next)

        bar.addWidget(QLabel('项目'))
        bar.addWidget(self.project_combo, 1)
        bar.addWidget(self.save_btn)
        bar.addWidget(self.next_btn)
        bar.addWidget(self.check_btn)
        bar.addWidget(self.pref_btn)
        self.layout.addLayout(bar)

    def _build_metric_strip(self):
        self.metric_box = QHBoxLayout()
        self.metric_box.setSpacing(8)
        self.metric_labels = {}
        for key, title, tone in [
            ('total', '样本总数', 'info'),
            ('saved', '已保存', 'success'),
            ('risk', '风险样本', 'warn'),
            ('issues', '打开问题', 'danger'),
            ('entities', '实体标注', 'info'),
            ('gate', '提交门禁', 'warn'),
        ]:
            lab = pill(f'{title} 0', tone)
            lab.setMinimumWidth(118)
            self.metric_labels[key] = lab
            self.metric_box.addWidget(lab)
        self.metric_box.addStretch()
        self.layout.addLayout(self.metric_box)

    def _build_work_area(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：压缩后的样本队列 + 风险筛选 + 标签统计
        left = QFrame()
        left.setProperty('card', True)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 10, 10, 10)
        ll.setSpacing(8)
        lh = QHBoxLayout()
        lh.addWidget(QLabel('文本样本队列'))
        self.queue_filter = QComboBox()
        self.queue_filter.addItems(['全部', '只看风险', '只看空文本', '只看重复', '只看已保存', '只看待处理'])
        self.queue_filter.currentIndexChanged.connect(self.reload_samples)
        lh.addWidget(self.queue_filter)
        ll.addLayout(lh)
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.list.currentRowChanged.connect(self.select_sample)
        ll.addWidget(self.list, 4)
        self.sample_snapshot = QTableWidget()
        self.sample_snapshot.setMaximumHeight(170)
        ll.addWidget(QLabel('当前队列快照'))
        ll.addWidget(self.sample_snapshot, 1)
        splitter.addWidget(left)

        # 中间：原文、实体操作、质量问题和相似样本压在一个区域
        mid = QFrame()
        mid.setProperty('card', True)
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(10, 10, 10, 10)
        ml.setSpacing(8)

        mh = QHBoxLayout()
        self.sample_title = QLabel('当前样本：未选择')
        self.sample_title.setProperty('sectionTitle', True)
        mh.addWidget(self.sample_title, 1)
        self.current_status = pill('未加载', 'info')
        mh.addWidget(self.current_status)
        ml.addLayout(mh)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText('原始文本 / Prompt / response 内容。支持直接编辑修正训练样本。')
        self.text_edit.setMinimumHeight(220)
        ml.addWidget(self.text_edit, 3)

        entbar = QHBoxLayout()
        self.entity_label = QComboBox()
        self.entity_label.addItems(['订单号', '商品名', '物流单号', '金额', '时间', '问题描述', '投诉对象', '地址'])
        entbtn = QPushButton('添加选中实体')
        entbtn.clicked.connect(self.add_entity)
        locate_btn = secondary(QPushButton('复制风险说明'))
        locate_btn.clicked.connect(self.copy_risk_hint)
        entbar.addWidget(QLabel('实体标签'))
        entbar.addWidget(self.entity_label, 1)
        entbar.addWidget(entbtn)
        entbar.addWidget(locate_btn)
        ml.addLayout(entbar)

        self.detail_tabs = QTabWidget()
        self.entity_table = QTableWidget()
        self.issue_table = QTableWidget()
        self.similar_table = QTableWidget()
        self.detail_tabs.addTab(self.entity_table, '实体结果')
        self.detail_tabs.addTab(self.issue_table, '质检问题')
        self.detail_tabs.addTab(self.similar_table, '相似/重复样本')
        ml.addWidget(self.detail_tabs, 2)
        splitter.addWidget(mid)

        # 右侧：把原来纵向散落的表单改成页签，减少空白和滚动
        right = QFrame()
        right.setProperty('card', True)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(10, 10, 10, 10)
        rl.setSpacing(8)
        self.right_tabs = QTabWidget()
        self.right_tabs.addTab(self._build_label_tab(), '分类')
        self.right_tabs.addTab(self._build_llm_tab(), '评分')
        self.right_tabs.addTab(self._build_gate_tab(), '门禁')
        self.right_tabs.addTab(self._build_spec_tab(), '规范')
        rl.addWidget(self.right_tabs, 1)
        splitter.addWidget(right)

        splitter.setSizes([285, 670, 390])
        self.layout.addWidget(splitter, 1)

    def _build_label_tab(self) -> QWidget:
        w = QWidget()
        gl = QGridLayout(w)
        gl.setContentsMargins(10, 10, 10, 10)
        gl.setSpacing(7)
        self.label_combo = QComboBox()
        self.multi_refund = QCheckBox('退款')
        self.multi_logistics = QCheckBox('物流')
        self.multi_complain = QCheckBox('投诉')
        self.multi_consult = QCheckBox('咨询')
        self.multi_after = QCheckBox('售后')
        self.multi_other = QCheckBox('其他')
        gl.addWidget(QLabel('单标签分类'), 0, 0, 1, 2)
        gl.addWidget(self.label_combo, 1, 0, 1, 2)
        gl.addWidget(QLabel('多标签/风险标签'), 2, 0, 1, 2)
        for idx, cb in enumerate([self.multi_refund, self.multi_logistics, self.multi_complain, self.multi_consult, self.multi_after, self.multi_other]):
            gl.addWidget(cb, 3 + idx // 2, idx % 2)
        self.tag_hint = QLabel('建议：单标签用于主意图，多标签用于风险、售后链路和复核分流。')
        self.tag_hint.setWordWrap(True)
        gl.addWidget(self.tag_hint, 7, 0, 1, 2)
        gl.setRowStretch(8, 1)
        return w

    def _build_llm_tab(self) -> QWidget:
        w = QWidget()
        gl = QGridLayout(w)
        gl.setContentsMargins(10, 10, 10, 10)
        gl.setSpacing(7)
        self.score = QSpinBox()
        self.score.setRange(1, 5)
        self.score.setValue(4)
        self.preference = QComboBox()
        self.preference.addItems(['A优于B', 'B优于A', '两者相当', '均不可用'])
        self.reason = QTextEdit()
        self.reason.setPlaceholderText('评价理由不少于10字，例如：A回答完整、礼貌且符合客服规范。')
        self.reason.setMinimumHeight(160)
        gl.addWidget(QLabel('质量评分'), 0, 0)
        gl.addWidget(self.score, 0, 1)
        gl.addWidget(QLabel('偏好选择'), 1, 0)
        gl.addWidget(self.preference, 1, 1)
        gl.addWidget(QLabel('评价理由'), 2, 0, 1, 2)
        gl.addWidget(self.reason, 3, 0, 1, 2)
        return w

    def _build_gate_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)
        self.gate_table = QTableWidget()
        lay.addWidget(self.gate_table, 2)
        self.quick_actions = QGroupBox('快速操作')
        qa = QGridLayout(self.quick_actions)
        auto_reason = secondary(QPushButton('补全评价理由'))
        auto_reason.clicked.connect(self.make_llm_eval)
        run_check = QPushButton('立即自检')
        run_check.clicked.connect(self.self_check)
        mark_hard = secondary(QPushButton('标记疑难'))
        mark_hard.clicked.connect(self.mark_hard_sample)
        qa.addWidget(auto_reason, 0, 0)
        qa.addWidget(run_check, 0, 1)
        qa.addWidget(mark_hard, 1, 0, 1, 2)
        lay.addWidget(self.quick_actions)
        return w

    def _build_spec_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setText(
            '文本标注规范\n\n'
            '1. 主标签必须表达用户最核心意图。\n'
            '2. 退款、物流、投诉、咨询、售后可作为多标签补充。\n'
            '3. 评价理由至少 10 字，应说明可训练价值与风险。\n'
            '4. 实体边界必须完整，不要漏掉订单号、商品名、物流单号。\n'
            '5. 空文本、重复文本、标签冲突和理由过短必须进入质检问题。\n'
            '6. 难以判断时标记疑难，交由质检员仲裁。'
        )
        lay.addWidget(txt)
        return w

    def refresh(self):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for p in list_projects():
            if p['data_type'] == '文本':
                self.project_combo.addItem(f"{p['code']}｜{p['name']}", p['id'])
        self.project_combo.blockSignals(False)
        self.project_changed()

    def project_changed(self):
        self.project_id = self.project_combo.currentData()
        self.label_combo.clear()
        if self.project_id:
            for l in get_labels(self.project_id):
                self.label_combo.addItem(l['name'])
        self.reload_samples()
        self.update_metrics()

    def reload_samples(self):
        self.list.clear()
        all_samples = list_samples(self.project_id, 'text') if self.project_id else []
        mode = self.queue_filter.currentText() if hasattr(self, 'queue_filter') else '全部'
        self.samples = []
        for s in all_samples:
            risk = s['risk_tags'] or '无风险'
            keep = (
                mode == '全部'
                or (mode == '只看风险' and risk != '无风险')
                or (mode == '只看空文本' and '空文本' in risk)
                or (mode == '只看重复' and ('重复' in risk or s.get('is_duplicate')))
                or (mode == '只看已保存' and s['status'] == '已保存')
                or (mode == '只看待处理' and s['status'] != '已保存')
            )
            if keep:
                self.samples.append(s)
        for s in self.samples:
            text = (s['text_content'] or '【空文本】').replace('\n', ' ')[:44]
            icon = '✓' if s['status'] == '已保存' else '•'
            if s['risk_tags'] and s['risk_tags'] != '无风险':
                icon = '⚠'
            item = QListWidgetItem(f"{icon} {s['sample_code']}｜{s['status']}｜{s['risk_tags'] or '无风险'}\n{text}")
            item.setData(Qt.ItemDataRole.UserRole, s['id'])
            self.list.addItem(item)
        if self.samples:
            self.list.setCurrentRow(0)
        self.update_snapshot(all_samples)
        self.update_metrics()

    def update_snapshot(self, samples: list[dict]):
        if not samples:
            fill_table(self.sample_snapshot, [], [('metric', '指标'), ('value', '数量')])
            return
        rows = [
            {'metric': '已保存', 'value': sum(1 for s in samples if s['status'] == '已保存')},
            {'metric': '风险', 'value': sum(1 for s in samples if (s['risk_tags'] or '无风险') != '无风险')},
            {'metric': '空文本', 'value': sum(1 for s in samples if '空文本' in (s['risk_tags'] or ''))},
            {'metric': '重复', 'value': sum(1 for s in samples if '重复' in (s['risk_tags'] or '') or s.get('is_duplicate'))},
        ]
        fill_table(self.sample_snapshot, rows, [('metric', '指标'), ('value', '数量')])

    def select_sample(self, row: int):
        if row < 0 or row >= len(getattr(self, 'samples', [])):
            return
        s = self.samples[row]
        self.sample_id = s['id']
        self.text_edit.setText(s['text_content'] or '')
        self.sample_title.setText(f"当前样本：{s['sample_code']}｜{s['risk_tags'] or '无风险'}")
        self.current_status.setText(s['status'])
        anns = annotations_for_sample(self.sample_id)
        self._clear_multi_tags()
        if anns:
            idx = self.label_combo.findText(anns[0]['label'])
            if idx >= 0:
                self.label_combo.setCurrentIndex(idx)
            self.reason.setText(anns[0].get('comment') or '')
            self._check_multi_tags([a['label'] for a in anns])
        self.reload_entities_and_issues()
        self.update_metrics()

    def _clear_multi_tags(self):
        for cb in [self.multi_refund, self.multi_logistics, self.multi_complain, self.multi_consult, self.multi_after, self.multi_other]:
            cb.setChecked(False)

    def _check_multi_tags(self, labels: list[str]):
        mapping = {
            '退款': self.multi_refund,
            '物流': self.multi_logistics,
            '投诉': self.multi_complain,
            '咨询': self.multi_consult,
            '售后': self.multi_after,
            '其他': self.multi_other,
        }
        for lab in labels:
            if lab in mapping:
                mapping[lab].setChecked(True)

    def save_text_annotation(self):
        if not self.sample_id:
            return
        execute("UPDATE samples SET text_content=?, status='已保存' WHERE id=?", (self.text_edit.toPlainText(), self.sample_id))
        anns = annotations_for_sample(self.sample_id)
        label = self.label_combo.currentText()
        comment = self.reason.toPlainText()
        if anns:
            execute("UPDATE annotations SET label=?, comment=?, status='已确认', updated_at=CURRENT_TIMESTAMP WHERE id=?", (label, comment, anns[0]['id']))
        else:
            execute("INSERT INTO annotations(sample_id,label,annotation_type,confidence,source,status,created_by,comment) VALUES(?,?,?,?,?,?,?,?)", (self.sample_id, label, 'text_class', 1, '人工', '已确认', self.user['username'], comment))
        # 记录多标签，避免重复插入同一标签
        selected = [cb.text() for cb in [self.multi_refund, self.multi_logistics, self.multi_complain, self.multi_consult, self.multi_after, self.multi_other] if cb.isChecked()]
        existing = {a['label'] for a in annotations_for_sample(self.sample_id)}
        for lab in selected:
            if lab not in existing:
                execute("INSERT INTO annotations(sample_id,label,annotation_type,confidence,source,status,created_by,comment) VALUES(?,?,?,?,?,?,?,?)", (self.sample_id, lab, 'multi_label', 1, '人工', '已确认', self.user['username'], '多标签/风险标签'))
        log_action(self.user['username'], '保存文本标注', f"样本{self.sample_id} 标签{label}")
        self.reload_entities_and_issues()
        self.update_metrics()
        self.current_status.setText('已保存')

    def save_and_next(self):
        self.save_text_annotation()
        row = self.list.currentRow()
        if row + 1 < self.list.count():
            self.list.setCurrentRow(row + 1)
        else:
            QMessageBox.information(self, '任务完成', '当前筛选队列已处理到最后一条。')

    def add_entity(self):
        if not self.sample_id:
            return
        cur = self.text_edit.textCursor()
        selected = cur.selectedText()
        if not selected:
            QMessageBox.warning(self, '未选择文本', '请在文本框中选中一个片段后再添加实体。')
            return
        start = cur.selectionStart()
        end = cur.selectionEnd()
        label = self.entity_label.currentText()
        execute("INSERT INTO annotations(sample_id,label,annotation_type,entity_start,entity_end,entity_text,confidence,source,status,created_by,comment) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (self.sample_id, label, 'entity', start, end, selected, 1, '人工', '已确认', self.user['username'], '实体边界人工标注'))
        self.reload_entities_and_issues()
        self.update_metrics()
        QMessageBox.information(self, '实体已添加', f'已添加实体：{label} = {selected}')

    def self_check(self):
        if not self.sample_id:
            return
        self.save_text_annotation()
        issues = run_quality_check(self.sample_id, self.user['username'])
        QMessageBox.information(self, '文本质量自检完成', f'检出 {len(issues)} 个文本质量问题，已刷新质检问题页签。')
        self.reload_entities_and_issues()
        self.update_metrics()

    def make_llm_eval(self):
        self.preference.setCurrentIndex(0)
        self.score.setValue(4)
        self.reason.setText('A回答更完整、礼貌且能覆盖用户核心诉求；B回答态度生硬，缺少可执行处理方案，不适合作为训练样本。')
        self.right_tabs.setCurrentIndex(1)
        QMessageBox.information(self, '评分建议已生成', '系统已根据安全性、完整性、指令遵循和表达质量生成评价建议，可人工修改后保存。')

    def mark_hard_sample(self):
        if not self.sample_id:
            return
        execute("UPDATE samples SET risk_tags='疑难样本' WHERE id=?", (self.sample_id,))
        log_action(self.user['username'], '标记疑难文本样本', f'样本{self.sample_id}')
        self.reload_samples()
        QMessageBox.information(self, '已标记疑难', '样本已进入疑难/仲裁视角，可由质检员复核。')

    def copy_risk_hint(self):
        if not self.sample_id:
            return
        issues = fetch_all("SELECT issue_type,severity,suggestion FROM quality_issues WHERE sample_id=? ORDER BY id DESC LIMIT 3", (self.sample_id,))
        if issues:
            self.reason.setText('\n'.join([f"{i['severity']}风险：{i['issue_type']}，建议：{i['suggestion']}" for i in issues]))
        else:
            self.reason.setText('当前样本暂无自动质检问题，可从用户意图、标签一致性和可训练价值角度填写评价理由。')

    def reload_entities_and_issues(self):
        entities = []
        issues = []
        similar = []
        gates = []
        if self.sample_id:
            entities = fetch_all("SELECT annotation_type,label,entity_text,entity_start,entity_end,comment FROM annotations WHERE sample_id=? AND annotation_type='entity' ORDER BY id DESC", (self.sample_id,))
            issues = fetch_all("SELECT issue_type,severity,position_text,suggestion,status FROM quality_issues WHERE sample_id=? ORDER BY id DESC", (self.sample_id,))
            current = fetch_one("SELECT text_content,risk_tags,status FROM samples WHERE id=?", (self.sample_id,))
            if current and current['text_content']:
                key = current['text_content'][:8]
                similar = fetch_all("SELECT sample_code,status,risk_tags,text_content FROM samples WHERE project_id=? AND id<>? AND sample_type='text' AND text_content LIKE ? LIMIT 8", (self.project_id, self.sample_id, f'%{key}%'))
            text_len = len(self.text_edit.toPlainText().strip())
            reason_len = len(self.reason.toPlainText().strip())
            gates = [
                {'item': '主标签', 'result': '通过' if self.label_combo.currentText() else '阻断', 'advice': '必须选择单标签分类'},
                {'item': '文本长度', 'result': '通过' if text_len >= 5 else '阻断', 'advice': f'当前{text_len}字，过短会影响训练'},
                {'item': '评价理由', 'result': '通过' if reason_len >= 10 else '提醒', 'advice': f'当前{reason_len}字，建议不少于10字'},
                {'item': '质检问题', 'result': '通过' if not issues else f'{len(issues)}项待处理', 'advice': '存在问题时先处理再提交'},
            ]
        fill_table(self.entity_table, entities, [('annotation_type', '类型'), ('label', '实体标签'), ('entity_text', '实体文本'), ('entity_start', '起始'), ('entity_end', '结束'), ('comment', '备注')])
        fill_table(self.issue_table, issues, [('issue_type', '问题'), ('severity', '严重度'), ('position_text', '位置'), ('status', '状态'), ('suggestion', '建议')])
        fill_table(self.similar_table, similar, [('sample_code', '样本'), ('status', '状态'), ('risk_tags', '风险'), ('text_content', '文本摘要')])
        fill_table(self.gate_table, gates, [('item', '门禁项'), ('result', '结果'), ('advice', '处理建议')])

    def update_metrics(self):
        if not self.project_id:
            return
        rows = fetch_all("SELECT id,status,risk_tags FROM samples WHERE project_id=? AND sample_type='text'", (self.project_id,))
        total = len(rows)
        saved = sum(1 for r in rows if r['status'] == '已保存')
        risk = sum(1 for r in rows if (r['risk_tags'] or '无风险') != '无风险')
        issues = fetch_one("SELECT COUNT(*) c FROM quality_issues qi JOIN samples s ON qi.sample_id=s.id WHERE s.project_id=? AND s.sample_type='text' AND qi.status<>'已关闭'", (self.project_id,))
        entities = fetch_one("SELECT COUNT(*) c FROM annotations a JOIN samples s ON a.sample_id=s.id WHERE s.project_id=? AND s.sample_type='text' AND a.annotation_type='entity'", (self.project_id,))
        gate_text = '通过' if total and saved == total and (issues['c'] if issues else 0) == 0 else '待完善'
        values = {
            'total': f'样本总数 {total}',
            'saved': f'已保存 {saved}',
            'risk': f'风险样本 {risk}',
            'issues': f"打开问题 {issues['c'] if issues else 0}",
            'entities': f"实体标注 {entities['c'] if entities else 0}",
            'gate': f'提交门禁 {gate_text}',
        }
        for k, v in values.items():
            self.metric_labels[k].setText(v)
