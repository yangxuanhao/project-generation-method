from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QDialog, QFormLayout, QLineEdit, QComboBox, QTextEdit, QDialogButtonBox, QMessageBox, QLabel
from app.ui.utils import page_root, fill_table, secondary, make_project_combo
from app.services.dataset_service import list_projects, list_rules, add_rule


class AnnotationSpecPage(QWidget):
    def __init__(self, user: dict):
        super().__init__(); self.user = user
        root, self.layout = page_root('标注规范管理')
        wrap = QVBoxLayout(self); wrap.setContentsMargins(0,0,0,0); wrap.addWidget(root)
        bar = QHBoxLayout(); self.project_combo = make_project_combo(list_projects()); self.project_combo.currentIndexChanged.connect(self.refresh)
        add = QPushButton('新增规范/质检规则'); add.clicked.connect(self.add_rule_dialog)
        preview = secondary(QPushButton('弹出当前规范卡片')); preview.clicked.connect(self.preview_rules)
        bar.addWidget(QLabel('项目')); bar.addWidget(self.project_combo, 2); bar.addWidget(add); bar.addWidget(preview); bar.addStretch(); self.layout.addLayout(bar)
        self.table = QTableWidget(); self.layout.addWidget(self.table, 1)

    def refresh(self):
        rows = list_rules(self.project_combo.currentData()) if self.project_combo.currentData() else []
        fill_table(self.table, rows, [('rule_type','规则类型'),('title','规则名称'),('severity','严重程度'),('content','规范内容'),('enabled','启用')])

    def add_rule_dialog(self):
        dlg = QDialog(self); dlg.setWindowTitle('新增标注规范'); form = QFormLayout(dlg)
        rtype = QComboBox(); rtype.addItems(['图像','文本','大模型评价','返工','交付检查'])
        title = QLineEdit('疑难样本说明规则')
        severity = QComboBox(); severity.addItems(['高','中','低'])
        content = QTextEdit('标注员将样本标记为疑难时，必须选择疑难类型并填写不少于10字的说明。')
        for a,b in [('规则类型',rtype),('规则名称',title),('严重程度',severity),('规则内容',content)]: form.addRow(a,b)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel); form.addRow(buttons)
        buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)
        if dlg.exec():
            add_rule(self.project_combo.currentData(), {'rule_type':rtype.currentText(),'title':title.text(),'content':content.toPlainText(),'severity':severity.currentText()}, self.user['username'])
            QMessageBox.information(self, '新增成功', '规范已生效，可在标注工作台随时查看。')
            self.refresh()

    def preview_rules(self):
        rows = list_rules(self.project_combo.currentData())
        text = '\n\n'.join([f"【{r['severity']}】{r['title']}\n{r['content']}" for r in rows[:8]]) or '暂无规则'
        QMessageBox.information(self, '当前项目标注规范', text)
