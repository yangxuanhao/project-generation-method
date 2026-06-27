from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QDialog, QFormLayout, QLineEdit, QComboBox, QTextEdit, QCheckBox, QDialogButtonBox, QColorDialog, QMessageBox, QLabel
from app.ui.utils import page_root, fill_table, secondary, make_project_combo
from app.services.dataset_service import list_projects, get_labels, add_label


class LabelSchemaPage(QWidget):
    def __init__(self, user: dict):
        super().__init__(); self.user = user
        root, self.layout = page_root('标签体系管理')
        wrap = QVBoxLayout(self); wrap.setContentsMargins(0,0,0,0); wrap.addWidget(root)
        bar = QHBoxLayout(); self.project_combo = make_project_combo(list_projects()); self.project_combo.currentIndexChanged.connect(self.refresh)
        add = QPushButton('新增标签'); add.clicked.connect(self.add_label_dialog)
        export = secondary(QPushButton('模拟导出标签体系')); export.clicked.connect(lambda: QMessageBox.information(self,'导出完成','标签体系已导出为 JSON 模板（演示提示）。'))
        bar.addWidget(QLabel('项目')); bar.addWidget(self.project_combo, 2); bar.addWidget(add); bar.addWidget(export); bar.addStretch(); self.layout.addLayout(bar)
        self.table = QTableWidget(); self.layout.addWidget(self.table, 1)

    def refresh(self):
        if self.project_combo.count() == 0:
            self.project_combo.clear()
            for p in list_projects(): self.project_combo.addItem(f"{p['code']}｜{p['name']}", p['id'])
        rows = get_labels(self.project_combo.currentData()) if self.project_combo.currentData() else []
        fill_table(self.table, rows, [('name','标签名称'),('code','编码'),('color','颜色'),('label_type','类型'),('shortcut','快捷键'),('required','必填'),('exclusive','互斥'),('description','说明'),('positive_example','正例'),('negative_example','反例')])

    def add_label_dialog(self):
        dlg = QDialog(self); dlg.setWindowTitle('新增标签'); form = QFormLayout(dlg)
        name = QLineEdit('new_label'); code = QLineEdit('new_label'); color = QLineEdit('#14b8a6')
        pick = QPushButton('选择颜色'); pick.setProperty('secondary', True); pick.clicked.connect(lambda: color.setText(QColorDialog.getColor().name()))
        ltype = QComboBox(); ltype.addItems(['分类标签','目标框标签','多边形标签','点标签','线段标签','实体标签','评分标签','偏好标签'])
        shortcut = QLineEdit('N'); required = QCheckBox('必填'); exclusive = QCheckBox('与同组互斥')
        desc = QTextEdit('请输入标签定义、边界规则和适用场景。')
        pos = QTextEdit('正例：目标清晰、符合该标签定义。'); neg = QTextEdit('反例：容易混淆但不属于该标签的情况。')
        for a,b in [('标签名称',name),('标签编码',code),('颜色值',color),('',pick),('标签类型',ltype),('快捷键',shortcut),('必填',required),('互斥',exclusive),('标签说明',desc),('正例',pos),('反例',neg)]: form.addRow(a,b)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel); form.addRow(buttons)
        buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)
        if dlg.exec():
            add_label(self.project_combo.currentData(), {'name':name.text(),'code':code.text(),'color':color.text(),'label_type':ltype.currentText(),'shortcut':shortcut.text(),'required':required.isChecked(),'exclusive':exclusive.isChecked(),'description':desc.toPlainText(),'positive_example':pos.toPlainText(),'negative_example':neg.toPlainText(),'note':'由界面新增'}, self.user['username'])
            QMessageBox.information(self, '新增成功', '标签已加入当前项目，标注工作台会同步显示。')
            self.refresh()
