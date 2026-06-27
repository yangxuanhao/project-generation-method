from __future__ import annotations

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStackedWidget, QListWidget, QListWidgetItem, QSplitter, QFrame, QProgressBar, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from app.ui.app_state import AppState
from app.ui.canvas import CrackAnnotationCanvas
from app.ui.widgets import title_label
from app.core.quality import AnnotationQualityChecker
from app.core.geometry import polyline_length_real

from app.ui.panels.image_task_panel import ImageTaskPanel
from app.ui.panels.calibration_panel import CalibrationPanel
from app.ui.panels.drawing_panel import DrawingPanel
from app.ui.panels.snap_panel import SnapPanel
from app.ui.panels.width_panel import WidthPanel
from app.ui.panels.region_panel import RegionPanel
from app.ui.panels.diagnosis_panel import DiagnosisPanel
from app.ui.panels.missing_panel import MissingPanel
from app.ui.panels.street_view_panel import StreetViewPanel
from app.ui.panels.review_panel import ReviewPanel
from app.ui.panels.repair_panel import RepairPanel
from app.ui.panels.statistics_panel import StatisticsPanel
from app.ui.panels.report_panel import ReportPanel


class MainWindow(QMainWindow):
    PANEL_CLASSES = [
        ('影像任务舱', ImageTaskPanel),
        ('比例标定舱', CalibrationPanel),
        ('裂缝描绘舱', DrawingPanel),
        ('磁吸辅助舱', SnapPanel),
        ('宽度卡尺舱', WidthPanel),
        ('网裂圈选舱', RegionPanel),
        ('病害诊断舱', DiagnosisPanel),
        ('自动标注舱', MissingPanel),
        ('街景标注舱', StreetViewPanel),
        ('复核纠偏舱', ReviewPanel),
        ('修复估算舱', RepairPanel),
        ('路段统计舱', StatisticsPanel),
        ('成果报告舱', ReportPanel),
    ]

    def __init__(self, storage, user, project_root: Path):
        super().__init__()
        self.storage = storage
        self.user = user
        self.project_root = Path(project_root)
        self.state = AppState()
        self.state.set_tasks(self.storage.load_tasks())
        self.setWindowTitle('路面裂缝人工标注与测量辅助软件')
        self.resize(1560, 930)
        self._build_ui()
        self._connect_signals()
        self.refresh_all()
        self.select_panel(0)
        if not self.state.tasks:
            QTimer.singleShot(500, lambda: self.statusBar().showMessage('建议先在影像任务舱打开内置样例影像，再进行标注。', 8000))

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.addWidget(title_label('路面裂缝人工标注与测量辅助软件'))
        subtitle = QLabel('白色清爽风｜类PS工作台｜支持自动识别 + 人工修正')
        subtitle.setStyleSheet('color:#6a7d95; font-size:12px;')
        title_row.addWidget(subtitle)
        title_row.addStretch(1)
        self.user_label = QLabel(f'当前用户：{self.user.username}｜角色：{self.user.role}')
        self.user_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        title_row.addWidget(self.user_label)
        root_layout.addLayout(title_row)

        quick_row = QHBoxLayout()
        for text, mode in [('浏览', '浏览'), ('描绘裂缝', '折线裂缝'), ('宽度卡尺', '宽度卡尺'), ('网裂圈选', '网裂圈选'), ('比例标定', '比例标定')]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked=False, m=mode: self.state.set_mode(m))
            quick_row.addWidget(btn)
        quick_row.addStretch(1)
        del_btn = QPushButton('删除选中标注线')
        del_btn.clicked.connect(self.delete_selected_annotation)
        quick_row.addWidget(del_btn)
        save_btn = QPushButton('保存全部任务'); save_btn.setObjectName('PrimaryButton'); save_btn.clicked.connect(self.save_all)
        quick_row.addWidget(save_btn)
        root_layout.addLayout(quick_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter, 1)

        left = self._build_left_menu(); splitter.addWidget(left)

        center = QWidget(); center_layout = QVBoxLayout(center); center_layout.setContentsMargins(6, 0, 6, 0)
        self.canvas = CrackAnnotationCanvas(self.state)
        self.track = QListWidget(); self.track.setMaximumHeight(120); self.track.itemClicked.connect(self.track_clicked)
        center_layout.addWidget(self.canvas, 1)
        center_layout.addWidget(QLabel('量测轨道条：点击裂缝块可定位并选中，浏览模式下可拖动节点修正。'))
        center_layout.addWidget(self.track)
        splitter.addWidget(center)

        right = QWidget(); right_layout = QVBoxLayout(right); right_layout.setContentsMargins(6, 0, 0, 0)
        self.quality_bar = QProgressBar(); self.quality_bar.setRange(0, 100)
        right_layout.addWidget(QLabel('标注质量评分'))
        right_layout.addWidget(self.quality_bar)
        self.stack = QStackedWidget(); self.panels = []
        for _, cls in self.PANEL_CLASSES:
            panel = cls(self.state, self.storage, self.project_root, self.canvas)
            self.panels.append(panel)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setWidget(panel)
            self.stack.addWidget(scroll)

        # 上方功能区是主要操作区，给予更多空间
        right_layout.addWidget(self.stack, 1)

        # 诊断卡片流改为紧凑信息条，避免空白列表长期占用大面积高度
        self.crack_cards_title = QLabel('裂缝诊断卡片流（紧凑）')
        self.crack_cards_title.setStyleSheet('color:#223042; font-weight:600; margin-top:4px;')
        right_layout.addWidget(self.crack_cards_title)
        self.crack_cards = QListWidget()
        self.crack_cards.setMinimumHeight(64)
        self.crack_cards.setMaximumHeight(118)
        self.crack_cards.setAlternatingRowColors(True)
        self.crack_cards.itemClicked.connect(self.card_clicked)
        right_layout.addWidget(self.crack_cards, 0)

        splitter.addWidget(right)
        splitter.setSizes([185, 900, 500])

        self.statusBar().showMessage('系统已启动')

    def _build_left_menu(self):
        frame = QFrame(); frame.setObjectName('PanelCard')
        layout = QVBoxLayout(frame); layout.setContentsMargins(10, 12, 10, 12)
        layout.addWidget(QLabel('功能工作舱'))
        self.menu_buttons = []
        for idx, (name, _) in enumerate(self.PANEL_CLASSES):
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked=False, i=idx: self.select_panel(i))
            self.menu_buttons.append(btn); layout.addWidget(btn)
        layout.addStretch(1)
        return frame

    def _connect_signals(self):
        self.state.task_changed.connect(self.refresh_all)
        self.state.selection_changed.connect(self.refresh_all)
        self.state.message.connect(lambda msg: self.statusBar().showMessage(msg, 6000))
        self.state.view_flags_changed.connect(self.canvas.update)
        self.canvas.canvas_changed.connect(self.refresh_all)
        self.canvas.request_save.connect(self.save_all)

    def select_panel(self, index: int):
        # 只有比例标定、裂缝描绘、宽度卡尺、网裂圈选这几个页面会继续响应图像标注点击。
        # 进入诊断、复核、统计、报告等评定页面时，自动切回浏览模式，避免误触继续画点。
        edit_pages = {1, 2, 4, 5}
        if index not in edit_pages and self.state.mode in ('折线裂缝', '网裂圈选', '比例标定', '宽度卡尺'):
            if self.state.mode == '折线裂缝' and len(self.state.temporary_points) >= 2:
                self.canvas.finish_polyline()
            elif self.state.mode == '网裂圈选' and len(self.state.region_pending_points) >= 3:
                self.canvas.finish_region()
            self.state.set_mode('浏览')

        # 进入病害诊断舱时，如果已有裂缝但未选中，自动选中第一条，避免“不能诊断”的空状态。
        if index == 6 and self.state.current_task and not self.state.selected_crack_id and self.state.current_task.cracks:
            self.state.select_crack(self.state.current_task.cracks[0].crack_id)

        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.menu_buttons):
            btn.setObjectName('PrimaryButton' if i == index else '')
            btn.style().unpolish(btn); btn.style().polish(btn)
        self.statusBar().showMessage(f'已进入：{self.PANEL_CLASSES[index][0]}', 5000)

    def refresh_all(self):
        self.refresh_crack_cards(); self.refresh_track(); self.refresh_quality(); self.canvas.update()

    def refresh_quality(self):
        task = self.state.current_task
        score, details = AnnotationQualityChecker.score(task) if task else (0, ['未选择任务'])
        self.quality_bar.setValue(score); self.quality_bar.setFormat(f'{score}分')
        self.quality_bar.setToolTip('；'.join(details[:6]) if score < 85 else '质量状态较好')

    def refresh_crack_cards(self):
        self.crack_cards.clear(); task = self.state.current_task
        if not task:
            self.crack_cards.addItem('暂无任务：上方功能区可先导入影像或打开样例')
            return
        if not task.cracks:
            self.crack_cards.addItem('暂无裂缝：可在自动标注舱识别，或在裂缝描绘舱手工标注')
            return
        for crack in task.cracks:
            length = polyline_length_real(crack.points, task.meter_per_pixel)
            if not task.meter_per_pixel:
                length = length / 180
            text = (
                f'{crack.crack_id}｜{crack.source}｜{crack.crack_type}｜{crack.severity}\n'
                f'长{length:.2f}m｜均宽{crack.avg_width_mm:.2f}mm｜最大{crack.max_width_mm:.2f}mm｜{crack.review_status}'
            )
            item = QListWidgetItem(text); item.setData(Qt.ItemDataRole.UserRole, crack.crack_id)
            self.crack_cards.addItem(item)
            if crack.crack_id == self.state.selected_crack_id:
                self.crack_cards.setCurrentItem(item)

    def refresh_track(self):
        self.track.clear(); task = self.state.current_task
        if not task: return
        for crack in task.cracks:
            length = polyline_length_real(crack.points, task.meter_per_pixel)
            if not task.meter_per_pixel:
                length = length / 180
            block = '█' * max(2, min(28, int(length * 3) + 2))
            text = f'{block}  {crack.crack_id}｜{crack.severity}｜{length:.2f}米｜{crack.review_status}'
            item = QListWidgetItem(text); item.setData(Qt.ItemDataRole.UserRole, crack.crack_id)
            self.track.addItem(item)

    def card_clicked(self, item):
        self.state.select_crack(item.data(Qt.ItemDataRole.UserRole)); self.state.set_mode('浏览')

    def track_clicked(self, item):
        self.state.select_crack(item.data(Qt.ItemDataRole.UserRole)); self.state.set_mode('浏览')

    def delete_selected_annotation(self):
        ok, msg = self.canvas.delete_selected_any_annotation()
        self.statusBar().showMessage(msg, 5000)
        self.refresh_all()

    def save_all(self):
        self.storage.save_tasks(self.state.tasks)
        self.statusBar().showMessage('全部任务已保存', 4000)

    def closeEvent(self, event):
        self.save_all(); event.accept()
