"""业务规则配置器 - 图形化条件/动作配置、冲突检测、规则模板"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QGridLayout, QComboBox, QLineEdit, QSpinBox, QTextEdit, QListWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QSplitter)
from PyQt6.QtCore import Qt
from core.auth import Role, OpAction, auth_engine
from core.rule_engine import (rule_engine, TriggerType, LogicOp, CompareOp,
    Condition, RuleAction, Rule)

class RuleConfigWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._setup_ui(); self._load_rules()

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        left_panel = QVBoxLayout()
        left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)

        create_gb = QGroupBox("📝 创建/编辑规则")
        cl = QVBoxLayout()
        cl.addWidget(QLabel("规则名称:"))
        self.rule_name = QLineEdit("新规则"); cl.addWidget(self.rule_name)
        cl.addWidget(QLabel("触发方式:"))
        self.trigger_combo = QComboBox()
        self.trigger_combo.addItems([t.value for t in TriggerType]); cl.addWidget(self.trigger_combo)
        cl.addWidget(QLabel("优先级:"))
        self.priority_spin = QSpinBox(); self.priority_spin.setRange(1, 10); self.priority_spin.setValue(5)
        cl.addWidget(self.priority_spin)

        cl.addWidget(QLabel("条件字段+值:"))
        cond_row = QHBoxLayout()
        self.cond_field = QLineEdit("accuracy"); self.cond_value = QLineEdit("0.8")
        self.cond_op = QComboBox()
        self.cond_op.addItems([op.value for op in CompareOp])
        cond_row.addWidget(self.cond_field); cond_row.addWidget(self.cond_op); cond_row.addWidget(self.cond_value)
        cl.addLayout(cond_row)

        cl.addWidget(QLabel("动作类型:"))
        action_row = QHBoxLayout()
        self.action_type = QComboBox()
        self.action_type.addItems(["alert", "log", "abort", "transform", "route"])
        self.action_param = QLineEdit('{"msg":"条件满足"}')
        action_row.addWidget(self.action_type); action_row.addWidget(self.action_param)
        cl.addLayout(action_row)

        btn_row = QHBoxLayout()
        btn_row.addWidget(QPushButton("➕ 添加规则", clicked=self._add_rule))
        btn_row.addWidget(QPushButton("💾 存为模板", clicked=self._save_template))
        btn_row.addWidget(QPushButton("📋 从模板创建", clicked=self._from_template))
        cl.addLayout(btn_row)
        create_gb.setLayout(cl)
        left_panel.addWidget(create_gb)

        conflict_gb = QGroupBox("⚠ 冲突检测")
        cfl = QVBoxLayout()
        self.conflict_text = QTextEdit(); self.conflict_text.setReadOnly(True); self.conflict_text.setMaximumHeight(100)
        cfl.addWidget(self.conflict_text)
        cfl.addWidget(QPushButton("🔍 检测冲突", clicked=self._detect_conflicts))
        cfl.addWidget(QPushButton("🔧 自动修复", clicked=self._auto_resolve))
        conflict_gb.setLayout(cfl)
        left_panel.addWidget(conflict_gb)

        left_widget = QWidget(); left_widget.setLayout(left_panel); left_widget.setMaximumWidth(320)

        right_panel = QVBoxLayout()
        self.rule_table = QTableWidget(0, 6)
        self.rule_table.setHorizontalHeaderLabels(["规则ID", "名称", "触发方式", "优先级", "启用", "分组"])
        self.rule_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rule_table.itemSelectionChanged.connect(self._on_rule_select)
        right_panel.addWidget(QLabel("📋 规则列表（可点击选择编辑）", styleSheet="color:#E65100;font-weight:bold;"))
        right_panel.addWidget(self.rule_table)

        exec_gb = QGroupBox("🧪 规则测试")
        el = QVBoxLayout()
        test_row = QHBoxLayout()
        self.test_context = QLineEdit('{"accuracy":0.92,"node_count":5}')
        test_row.addWidget(QLabel("上下文JSON:")); test_row.addWidget(self.test_context)
        el.addLayout(test_row)
        test_btn_row = QHBoxLayout()
        test_btn_row.addWidget(QPushButton("▶ 测试选中规则", clicked=self._test_rule))
        test_btn_row.addWidget(QPushButton("▶ 测试全部规则", clicked=self._test_all))
        test_btn_row.addWidget(QPushButton("🔄 切换启用", clicked=self._toggle_rule))
        test_btn_row.addWidget(QPushButton("🗑 删除规则", clicked=self._delete_rule))
        el.addLayout(test_btn_row)
        self.test_result = QTextEdit(); self.test_result.setReadOnly(True); self.test_result.setMaximumHeight(80)
        el.addWidget(self.test_result)
        exec_gb.setLayout(el)
        right_panel.addWidget(exec_gb)

        right_widget = QWidget(); right_widget.setLayout(right_panel)
        layout.addWidget(left_widget); layout.addWidget(right_widget, 1)

    def _add_rule(self):
        if not auth_engine.check_permission(self.user, "rule_config", OpAction.CREATE):
            QMessageBox.warning(self, "权限不足", "无创建规则权限"); return
        try:
            conditions = []
            if self.cond_field.text():
                op_map = {op.value: op for op in CompareOp}
                conditions = [Condition(field=self.cond_field.text(),
                    op=op_map.get(self.cond_op.currentText(), CompareOp.EQ),
                    value=self._parse_value(self.cond_value.text()))]
            actions = [RuleAction(action_type=self.action_type.currentText(),
                params=self._parse_json(self.action_param.text()))]
            trigger_map = {t.value: t for t in TriggerType}
            rule = rule_engine.create_rule(self.rule_name.text(),
                trigger_map[self.trigger_combo.currentText()],
                conditions, actions, self.priority_spin.value())
            QMessageBox.information(self, "成功", f"规则 [{rule.rule_id}] 已创建")
            self._load_rules()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _load_rules(self):
        rules = rule_engine.get_rules()
        self.rule_table.setRowCount(0)
        for rule in rules:
            r = self.rule_table.rowCount()
            self.rule_table.insertRow(r)
            for c, val in enumerate([rule.rule_id, rule.name, rule.trigger.value,
                str(rule.priority), "✅" if rule.enabled else "⛔", rule.group]):
                self.rule_table.setItem(r, c, QTableWidgetItem(str(val)))

    def _detect_conflicts(self):
        conflicts = rule_engine.detect_conflicts()
        if conflicts:
            msgs = "\n".join([f"⚠ {c['detail']} [{c['type']}]" for c in conflicts])
            self.conflict_text.setHtml(f'<span style="color:#D84315;">{msgs}</span>')
        else:
            self.conflict_text.setHtml('<span style="color:#2E7D32;">✓ 未检测到规则冲突</span>')

    def _auto_resolve(self):
        conflicts = rule_engine.detect_conflicts()
        resolved = 0
        for c in conflicts:
            if rule_engine.toggle_rule(c["rule_b"]): resolved += 1
        self.conflict_text.setHtml(f'<span style="color:#2E7D32;">已禁用 {resolved} 个冲突规则</span>')
        self._load_rules()

    def _test_rule(self):
        selected = self.rule_table.selectedItems()
        if not selected: return
        rid = self.rule_table.item(selected[0].row(), 0).text()
        try:
            context = eval(self.test_context.text())
            result = rule_engine.evaluate(rid, context)
            self.test_result.setHtml(f'<span style="color:{"#66bb6a" if result else "#ef5350"};">规则 {rid}: {"触发" if result else "未触发"}</span>')
        except Exception as e:
            self.test_result.setHtml(f'<span style="color:#D84315;">测试失败: {e}</span>')

    def _test_all(self):
        try:
            context = eval(self.test_context.text())
            fired = rule_engine.evaluate_all(context)
            names = [r.name for r in fired]
            self.test_result.setHtml(f'<span style="color:#E65100;">触发 {len(fired)} 条规则: {names}</span>')
        except Exception as e:
            self.test_result.setHtml(f'<span style="color:#D84315;">失败: {e}</span>')

    def _save_template(self):
        selected = self.rule_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择规则"); return
        rid = self.rule_table.item(selected[0].row(), 0).text()
        tid = rule_engine.save_as_template(rid, f"模板_{rid}")
        if tid: QMessageBox.information(self, "保存模板", f"模板 [{tid}] 已保存")

    def _from_template(self):
        QMessageBox.information(self, "模板", "请在模板列表中选择模板创建\n当前模板库: 2个预置模板")

    def _toggle_rule(self):
        selected = self.rule_table.selectedItems()
        if selected:
            rid = self.rule_table.item(selected[0].row(), 0).text()
            rule_engine.toggle_rule(rid); self._load_rules()

    def _delete_rule(self):
        selected = self.rule_table.selectedItems()
        if selected:
            rid = self.rule_table.item(selected[0].row(), 0).text()
            if rule_engine.delete_rule(rid): self._load_rules()

    def _on_rule_select(self):
        selected = self.rule_table.selectedItems()
        if selected:
            row = selected[0].row()
            self.rule_name.setText(self.rule_table.item(row, 1).text())

    def _parse_value(self, s: str):
        try: return eval(s)
        except: return s

    def _parse_json(self, s: str):
        try:
            import json; return json.loads(s)
        except: return {"msg": s}

def get_module_widget(user):
    return RuleConfigWidget(user)
