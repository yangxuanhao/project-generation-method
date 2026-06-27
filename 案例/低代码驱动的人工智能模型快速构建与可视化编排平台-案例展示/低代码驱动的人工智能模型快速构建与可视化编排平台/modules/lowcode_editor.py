"""低代码编辑器模块 - 脚本编辑、语法校验、模板管理、自定义片段"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QGroupBox, QSplitter, QTextEdit, QInputDialog, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from core.auth import Role, OpAction, auth_engine
from core.rule_engine import rule_engine, TriggerType, Condition, CompareOp, RuleAction
from ui.code_editor import LowCodeEditor, CODE_TEMPLATES

class LowCodeEditorModule(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._snippets = {}  # 用户自定义片段
        self._setup_ui()
        self._init_demo_rules()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("💻 低代码脚本编辑器")
        title.setStyleSheet("color:#4E342E;font-size:20px;font-weight:bold;")
        header.addWidget(title)
        header.addStretch()
        btn_new = QPushButton("📝 新建片段"); btn_new.clicked.connect(self._new_snippet)
        btn_export = QPushButton("📤 导出脚本"); btn_export.clicked.connect(self._export_script)
        btn_import = QPushButton("📥 导入脚本"); btn_import.clicked.connect(self._import_script)
        header.addWidget(btn_new); header.addWidget(btn_export); header.addWidget(btn_import)
        layout.addLayout(header)

        self.editor = LowCodeEditor()
        layout.addWidget(self.editor)

        bottom = QHBoxLayout()

        snippets_gb = QGroupBox("📁 自定义片段库")
        sl = QVBoxLayout()
        self.snippet_list = QListWidget()
        self.snippet_list.addItems(["自定义:数据增强", "自定义:特征工程", "自定义:模型评估", "自定义:数据清洗"])
        self.snippet_list.itemDoubleClicked.connect(self._load_snippet)
        sl.addWidget(self.snippet_list)
        snipt_btns = QHBoxLayout()
        snipt_btns.addWidget(QPushButton("💾 保存当前为片段", clicked=self._save_current_as_snippet))
        snipt_btns.addWidget(QPushButton("🗑 删除片段", clicked=self._delete_snippet))
        sl.addLayout(snipt_btns)
        snippets_gb.setLayout(sl)

        rule_gb = QGroupBox("📐 关联业务规则")
        rl = QVBoxLayout()
        self.rule_text = QTextEdit()
        self.rule_text.setReadOnly(True); self.rule_text.setMaximumHeight(120)
        self.rule_text.setPlainText("规则1: 脚本执行前必须通过语法检查 [优先级8]\n规则2: 模型训练脚本须含异常捕获 [优先级7]\n规则3: 数据处理脚本输出须包含数据量统计 [优先级6]")
        rl.addWidget(self.rule_text)
        rule_gb.setLayout(rl)

        bottom.addWidget(snippets_gb, 1)
        bottom.addWidget(rule_gb, 1)
        layout.addLayout(bottom)

        demo_bar = QHBoxLayout()
        demo_label = QLabel("📌 演示案例：点击左侧模板或自定义片段快速开始 | 支持Python语法实时高亮与校验")
        demo_label.setStyleSheet("color:#795548;font-size:11px;")
        demo_bar.addWidget(demo_label)
        layout.addLayout(demo_bar)

    def _init_demo_rules(self):
        for name, priority, cond_field, cond_val in [
            ("脚本语法检查规则", 9, "syntax_valid", True),
            ("异常处理检查规则", 7, "has_try_except", True),
            ("输出统计规则", 6, "has_output_stats", True),
        ]:
            rule_engine.create_rule(name, TriggerType.NODE,
                [Condition(field=cond_field, op=CompareOp.EQ, value=cond_val)],
                [RuleAction(action_type="log", params={"text": f"{name}通过"})],
                priority=priority, group="脚本编辑器")

    def _new_snippet(self):
        name, ok = QInputDialog.getText(self, "新建片段", "片段名称:")
        if ok and name:
            self.snippet_list.addItem(f"自定义:{name}")

    def _save_current_as_snippet(self):
        code = self.editor.get_code()
        if not code.strip():
            QMessageBox.warning(self, "提示", "请先编写代码"); return
        name, ok = QInputDialog.getText(self, "保存片段", "片段名称:")
        if ok and name:
            self._snippets[name] = code
            self.snippet_list.addItem(f"自定义:{name}")
            QMessageBox.information(self, "成功", f"片段 '{name}' 已保存")

    def _load_snippet(self, item):
        name = item.text().replace("自定义:", "")
        if name in self._snippets:
            self.editor.set_code(self._snippets[name])

    def _delete_snippet(self):
        current = self.snippet_list.currentItem()
        if current:
            name = current.text().replace("自定义:", "")
            self._snippets.pop(name, None)
            self.snippet_list.takeItem(self.snippet_list.currentRow())

    def _export_script(self):
        code = self.editor.get_code()
        if code.strip():
            QMessageBox.information(self, "导出", f"脚本已准备导出\n代码长度: {len(code)} 字符\n请使用数据管理模块保存到文件")

    def _import_script(self):
        QMessageBox.information(self, "导入", "请使用数据管理模块导入脚本文件")

def get_module_widget(user):
    return LowCodeEditorModule(user)
