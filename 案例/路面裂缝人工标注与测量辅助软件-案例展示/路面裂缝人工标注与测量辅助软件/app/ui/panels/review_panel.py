from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QListWidget, QMessageBox
from app.ui.widgets import PanelCard, primary_button, success_button, danger_button, InfoBox
from app.core.models import ReviewLog


class ReviewPanel(QWidget):
    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent); self.state=state; self.storage=storage; self.canvas=canvas
        layout=QVBoxLayout(self); card=PanelCard("复核纠偏舱")
        self.comment=QLineEdit(); self.comment.setPlaceholderText("输入复核意见，例如：线位偏移、宽度采样不足、类型需调整")
        card.layout.addWidget(QLabel("复核意见")); card.layout.addWidget(self.comment)
        pass_btn=success_button("通过并锁定选中裂缝"); pass_btn.clicked.connect(self.pass_crack); card.layout.addWidget(pass_btn)
        reject_btn=danger_button("退回修改选中裂缝"); reject_btn.clicked.connect(self.reject_crack); card.layout.addWidget(reject_btn)
        unlock=QPushButton("解除锁定"); unlock.clicked.connect(self.unlock); card.layout.addWidget(unlock)
        delete_line=danger_button("删除选中标注线"); delete_line.clicked.connect(self.delete_selected_line); card.layout.addWidget(delete_line)
        self.list=QListWidget(); card.layout.addWidget(QLabel("复核记录")); card.layout.addWidget(self.list)
        self.info=InfoBox(); card.layout.addWidget(self.info); layout.addWidget(card)
        self.state.selection_changed.connect(self.refresh); self.canvas.canvas_changed.connect(self.refresh) if self.canvas else None; self.refresh()

    def _log(self, result):
        task=self.state.current_task; crack=self.state.selected_crack()
        if not task or not crack: return None
        log=ReviewLog(crack_id=crack.crack_id, reviewer="当前复核员", result=result, comment=self.comment.text().strip())
        task.review_logs.append(log); crack.review_comment=log.comment; return log

    def pass_crack(self):
        crack=self.state.selected_crack(); task=self.state.current_task
        if not crack or not task: return
        crack.review_status='已通过'; crack.locked=True; self._log('通过并锁定')
        self.storage.upsert_task(task); self.canvas.update() if self.canvas else None; self.refresh(); QMessageBox.information(self,'复核通过',f'{crack.crack_id} 已锁定，防止误改')

    def reject_crack(self):
        crack=self.state.selected_crack(); task=self.state.current_task
        if not crack or not task: return
        crack.review_status='已退回'; crack.locked=False; self._log('退回修改')
        self.storage.upsert_task(task); self.canvas.update() if self.canvas else None; self.refresh(); QMessageBox.warning(self,'已退回','裂缝卡片和画布线条已进入退回状态')

    def unlock(self):
        crack=self.state.selected_crack(); task=self.state.current_task
        if not crack or not task: return
        crack.locked=False; crack.review_status='已修正待复核'; self._log('解除锁定')
        self.storage.upsert_task(task); self.canvas.update() if self.canvas else None; self.refresh(); QMessageBox.information(self,'已解除','可继续编辑该裂缝')

    def delete_selected_line(self):
        if not self.canvas:
            return
        ok, msg = self.canvas.delete_selected_any_annotation()
        self.refresh()
        QMessageBox.information(self, "删除标注线", msg)

    def refresh(self):
        self.list.clear(); task=self.state.current_task; crack=self.state.selected_crack()
        if task:
            for log in task.review_logs[-20:]: self.list.addItem(f"{log.created_at}｜{log.crack_id}｜{log.result}｜{log.comment}")
        self.info.setText(f"当前裂缝：{crack.crack_id}\n复核状态：{crack.review_status}\n锁定：{crack.locked}\n意见：{crack.review_comment}" if crack else "未选择裂缝。")
