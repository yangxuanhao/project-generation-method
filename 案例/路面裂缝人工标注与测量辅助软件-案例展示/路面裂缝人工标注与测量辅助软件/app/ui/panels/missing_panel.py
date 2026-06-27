from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QMessageBox, QComboBox
from app.ui.widgets import PanelCard, primary_button, danger_button, InfoBox
from app.core.missing_scanner import MissingCrackScanner
from app.core.auto_detect import CrackAutoDetector


class MissingPanel(QWidget):
    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.storage = storage
        self.canvas = canvas
        layout = QVBoxLayout(self)
        card = PanelCard('自动标注舱')

        card.layout.addWidget(QLabel('识别策略'))
        self.sensitivity = QComboBox()
        self.sensitivity.addItems(['保守', '标准', '增强'])
        self.sensitivity.setCurrentText('标准')
        card.layout.addWidget(self.sensitivity)

        auto_cover = primary_button('自动识别当前影像裂缝（覆盖旧识别）')
        auto_cover.clicked.connect(lambda: self.auto_detect_cracks(overwrite=True))
        card.layout.addWidget(auto_cover)

        auto_append = QPushButton('追加自动识别结果')
        auto_append.clicked.connect(lambda: self.auto_detect_cracks(overwrite=False))
        card.layout.addWidget(auto_append)

        scan = QPushButton('仅扫描疑似漏标暗线')
        scan.clicked.connect(self.scan)
        card.layout.addWidget(scan)

        delete_selected = danger_button('删除选中标注线')
        delete_selected.clicked.connect(self.delete_selected_line)
        card.layout.addWidget(delete_selected)

        delete_auto = QPushButton('删除全部自动识别标注线')
        delete_auto.clicked.connect(self.delete_auto_lines)
        card.layout.addWidget(delete_auto)

        ignore = QPushButton('忽略全部待确认候选')
        ignore.clicked.connect(self.ignore_all)
        card.layout.addWidget(ignore)

        clear_candidates = QPushButton('清空疑似候选线')
        clear_candidates.clicked.connect(self.clear_candidates)
        card.layout.addWidget(clear_candidates)

        self.list = QListWidget()
        self.list.setMaximumHeight(210)
        self.list.itemClicked.connect(self.select_from_list)
        card.layout.addWidget(QLabel('自动识别 / 候选列表'))
        card.layout.addWidget(self.list)
        self.info = InfoBox(
            '自动标注已改为局部暗线增强算法。默认“标准”策略会兼顾识别率和误检控制；'
            '如果图像裂缝很浅，再改用“标准”或“增强”。'
        )
        card.layout.addWidget(self.info)
        layout.addWidget(card)
        self.canvas.canvas_changed.connect(self.refresh) if self.canvas else None
        self.state.task_changed.connect(self.refresh)
        self.state.selection_changed.connect(self.refresh)
        self.refresh()

    def auto_detect_cracks(self, overwrite: bool = True):
        task = self.state.current_task
        if not task:
            return
        if overwrite:
            task.cracks = [c for c in task.cracks if c.source != '自动识别']
        strategy = self.sensitivity.currentText()
        cracks = CrackAutoDetector.detect_from_image(
            task.image_path,
            task.meter_per_pixel,
            sensitivity=strategy,
        )
        if not cracks:
            QMessageBox.warning(
                self,
                '识别结果',
                f'当前“{strategy}”策略未识别到明显裂缝。\n'
                '可尝试切换到“标准/增强”，或使用人工描绘模式。'
            )
            self.refresh()
            return
        task.cracks.extend(cracks)
        task.status = f'自动识别后待复核（{strategy}）'
        task.touch()
        self.storage.upsert_task(task)
        if cracks:
            self.state.select_crack(cracks[0].crack_id)
        if self.canvas:
            self.canvas.canvas_changed.emit()
            self.canvas.update()
        self.refresh()
        mode_text = '覆盖旧识别后' if overwrite else '追加'
        QMessageBox.information(
            self,
            '识别完成',
            f'{mode_text}生成 {len(cracks)} 条裂缝，识别策略：{strategy}。\n'
            '可在浏览模式选中裂缝节点并拖动，继续人工调整。'
        )

    def scan(self):
        task = self.state.current_task
        if not task or not self.canvas:
            return
        cands = MissingCrackScanner.scan_qimage(self.canvas.qimage, task.cracks, 10)
        task.candidates.extend(cands)
        task.touch()
        self.storage.upsert_task(task)
        self.canvas.canvas_changed.emit()
        self.canvas.update()
        self.refresh()
        QMessageBox.information(self, '扫描完成', f'发现 {len(cands)} 条疑似暗线候选')

    def delete_selected_line(self):
        if not self.canvas:
            return
        ok, msg = self.canvas.delete_selected_any_annotation()
        self.refresh()
        QMessageBox.information(self, '删除标注线', msg)

    def delete_auto_lines(self):
        if not self.canvas:
            return
        count = self.canvas.delete_auto_detected_annotations()
        self.refresh()
        QMessageBox.information(self, '删除自动识别线', f'已删除 {count} 条自动识别标注线')

    def ignore_all(self):
        task = self.state.current_task
        if not task:
            return
        for c in task.candidates:
            if c.status == '待确认':
                c.status = '已忽略'
        task.touch()
        self.storage.upsert_task(task)
        if self.canvas:
            self.canvas.canvas_changed.emit()
            self.canvas.update()
        self.refresh()

    def clear_candidates(self):
        if not self.canvas:
            return
        count = self.canvas.clear_candidates()
        self.refresh()
        QMessageBox.information(self, '清空候选线', f'已清空 {count} 条疑似候选线')

    def select_from_list(self, item):
        data = item.data(256)
        if isinstance(data, str) and data.startswith('裂缝-'):
            self.state.select_crack(data)

    def refresh(self):
        self.list.clear()
        task = self.state.current_task
        if not task:
            self.info.setText('尚未选择任务。请先在影像任务舱或街景标注舱打开图片。')
            return
        for c in task.cracks[-40:]:
            self.list.addItem(f'裂缝｜{c.crack_id}｜{c.source}｜{c.severity}｜节点{len(c.points)}')
            self.list.item(self.list.count() - 1).setData(256, c.crack_id)
        for c in task.candidates:
            self.list.addItem(f'候选｜{c.candidate_id}｜得分{c.score:.0f}｜{c.status}')
        self.info.setText(
            f'当前任务裂缝数：{len(task.cracks)}\n'
            f'自动识别裂缝：{len([x for x in task.cracks if x.source == "自动识别"])}\n'
            f'待确认候选：{len([x for x in task.candidates if x.status == "待确认"])}\n'
            f'当前策略：{self.sensitivity.currentText()}\n'
            '建议：默认用“标准”；如果误检仍多，切换“保守”；漏检明显时再用“增强”。'
        )
