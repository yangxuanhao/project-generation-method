from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QLabel, QMessageBox, QTextEdit, QDialog, QFormLayout, QDialogButtonBox
from app.ui.utils import page_root, fill_table, make_project_combo, secondary
from app.services.dataset_service import list_projects
from app.services.rework_service import list_reworks, update_rework_status


class ReworkPage(QWidget):
    def __init__(self, user: dict):
        super().__init__(); self.user=user
        root,self.layout=page_root('返工闭环管理')
        wrap=QVBoxLayout(self); wrap.setContentsMargins(0,0,0,0); wrap.addWidget(root)
        bar=QHBoxLayout(); self.project_combo=make_project_combo(list_projects()); self.project_combo.currentIndexChanged.connect(self.refresh)
        start=QPushButton('领取/开始返工'); start.clicked.connect(lambda:self.update_status('返工中'))
        submit=QPushButton('返工完成并二次提交'); submit.clicked.connect(lambda:self.update_status('已提交'))
        review=QPushButton('二次质检通过'); review.clicked.connect(lambda:self.update_status('通过'))
        reject=secondary(QPushButton('再次退回/仲裁处理')); reject.clicked.connect(self.arbitrate)
        for w in [QLabel('项目'),self.project_combo,start,submit,review,reject]: bar.addWidget(w)
        bar.addStretch(); self.layout.addLayout(bar)
        self.table=QTableWidget(); self.layout.addWidget(self.table,1)

    def refresh(self):
        rows=list_reworks(self.project_combo.currentData()) if self.project_combo.currentData() else []
        fill_table(self.table, rows, [('id','ID'),('rework_code','返工编号'),('sample_code','样本'),('filename','文件'),('labeler','标注员'),('reviewer','质检员'),('issue_type','问题类型'),('issue_desc','问题说明'),('requirement','返工要求'),('deadline','截止'),('status','状态'),('second_review','二次结论')])

    def selected_id(self):
        row=self.table.currentRow()
        if row<0: QMessageBox.warning(self,'未选择返工单','请先选择一条返工单。'); return None
        return int(self.table.item(row,0).text())

    def update_status(self,status):
        rid=self.selected_id();
        if not rid: return
        update_rework_status(rid,status,self.user['username'],f'{self.user["display_name"]} 操作：{status}')
        QMessageBox.information(self,'状态已更新',f'返工单已更新为：{status}。')
        self.refresh()

    def arbitrate(self):
        rid=self.selected_id();
        if not rid: return
        dlg=QDialog(self); dlg.setWindowTitle('仲裁/再次退回'); form=QFormLayout(dlg)
        note=QTextEdit('多次返工后仍存在类别边界分歧，建议由项目管理员仲裁并更新标注规范。')
        form.addRow('仲裁意见',note); buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel); form.addRow(buttons)
        buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)
        if dlg.exec():
            update_rework_status(rid,'仲裁处理',self.user['username'],note.toPlainText())
            QMessageBox.information(self,'已进入仲裁','返工单已进入仲裁处理状态，意见已记录。')
            self.refresh()
