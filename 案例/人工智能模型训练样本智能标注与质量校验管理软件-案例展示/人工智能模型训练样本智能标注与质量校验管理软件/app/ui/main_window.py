from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QStackedWidget, QFrame, QMessageBox, QScrollArea
from PyQt6.QtCore import Qt
from app.core.config import APP_NAME
from app.core.permissions import can_access
from app.ui.dashboard_page import DashboardPage
from app.ui.dataset_page import DatasetPage
from app.ui.import_page import ImportPage
from app.ui.label_schema_page import LabelSchemaPage
from app.ui.annotation_spec_page import AnnotationSpecPage
from app.ui.annotation_workbench import AnnotationWorkbench
from app.ui.text_annotation_page import TextAnnotationPage
from app.ui.quality_center_page import QualityCenterPage
from app.ui.consensus_page import ConsensusPage
from app.ui.ground_truth_page import GroundTruthPage
from app.ui.rework_page import ReworkPage
from app.ui.version_page import VersionPage
from app.ui.export_page import ExportPage
from app.ui.report_page import ReportPage
from app.ui.log_page import LogPage
from app.ui.utils import ghost, pill


class MainWindow(QMainWindow):
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.setWindowTitle(APP_NAME)
        self.resize(1320, 820)
        self.setMinimumSize(1120, 720)
        root = QWidget(); root.setObjectName('mainRoot'); self.setCentralWidget(root)
        main = QHBoxLayout(root); main.setContentsMargins(0, 0, 0, 0); main.setSpacing(0)

        self.nav = QFrame(); self.nav.setFixedWidth(246)
        self.nav.setStyleSheet('''
            QFrame{background:#08111f;color:white;border:none;}
            QLabel#brand{font-size:18px;font-weight:900;color:white;line-height:1.4;}
            QLabel#brandSub{font-size:12px;color:#93c5fd;}
            QLabel#navGroup{font-size:12px;color:#64748b;font-weight:800;margin-top:8px;}
            QPushButton{background:transparent;text-align:left;padding:8px 10px;border-radius:10px;color:#cbd5e1;font-weight:700;}
            QPushButton:hover{background:#132033;color:white;}
            QPushButton:checked{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2563eb,stop:1 #0ea5e9);color:white;}
            QPushButton:disabled{color:#475569;}
        ''')
        nav_layout = QVBoxLayout(self.nav); nav_layout.setContentsMargins(12, 12, 12, 12); nav_layout.setSpacing(7)
        title = QLabel(APP_NAME); title.setObjectName('brand'); title.setWordWrap(True)
        subtitle = QLabel('训练样本生产中台 / 质量闭环引擎'); subtitle.setObjectName('brandSub')
        nav_layout.addWidget(title); nav_layout.addWidget(subtitle)
        role_line = QHBoxLayout(); role_line.addWidget(pill(user['display_name'], 'info')); role_line.addWidget(pill(user['role'], 'success')); role_line.addStretch(); nav_layout.addLayout(role_line)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame); scroll.setStyleSheet('background:transparent;border:none;')
        nav_inner = QWidget(); nav_inner.setStyleSheet('background:transparent;')
        self.nav_buttons_layout = QVBoxLayout(nav_inner); self.nav_buttons_layout.setContentsMargins(0, 8, 0, 8); self.nav_buttons_layout.setSpacing(5)
        scroll.setWidget(nav_inner); nav_layout.addWidget(scroll, 1)

        shell = QWidget(); shell_layout = QVBoxLayout(shell); shell_layout.setContentsMargins(0,0,0,0); shell_layout.setSpacing(0)
        topbar = QFrame(); topbar.setFixedHeight(58); topbar.setStyleSheet('QFrame{background:#ffffff;border-bottom:1px solid #dbe4f0;}')
        top_l = QHBoxLayout(topbar); top_l.setContentsMargins(18, 0, 18, 0)
        self.page_title = QLabel(''); self.page_title.setStyleSheet('font-size:18px;font-weight:900;color:#0f172a;')
        self.page_hint = QLabel(''); self.page_hint.setStyleSheet('color:#64748b;')
        title_box = QVBoxLayout(); title_box.setSpacing(2); title_box.addWidget(self.page_title); title_box.addWidget(self.page_hint)
        top_l.addLayout(title_box); top_l.addStretch()
        self.state_chip = pill('本地SQLite · 演示数据', 'info'); top_l.addWidget(self.state_chip)
        self.quick_submit = QPushButton('进入工作台'); self.quick_submit.clicked.connect(lambda: self.switch_by_name('样本标注生产工作台'))
        top_l.addWidget(self.quick_submit)
        shell_layout.addWidget(topbar)

        self.stack = QStackedWidget(); shell_layout.addWidget(self.stack, 1)
        self.pages = []
        groups = [
            ('总览与项目', [('数据集驾驶舱', '▣', DashboardPage), ('数据集项目管理', '◫', DatasetPage), ('样本导入与数据体检', '⇪', ImportPage)]),
            ('生产配置', [('标签体系管理', '🏷', LabelSchemaPage), ('标注规范管理', '📐', AnnotationSpecPage)]),
            ('标注生产', [('样本标注生产工作台', '⌖', AnnotationWorkbench), ('文本标注工作台', '✎', TextAnnotationPage)]),
            ('质量闭环', [('质量校验中心', '✓', QualityCenterPage), ('多人一致性分析', '≋', ConsensusPage), ('Ground Truth 抽检', '◎', GroundTruthPage), ('返工闭环管理', '↺', ReworkPage)]),
            ('交付与审计', [('数据集版本管理', '⎇', VersionPage), ('训练格式导出中心', '⇲', ExportPage), ('报告生成中心', '▤', ReportPage), ('操作日志', '≡', LogPage)]),
        ]
        for group_name, page_classes in groups:
            group_label = QLabel(group_name); group_label.setObjectName('navGroup'); self.nav_buttons_layout.addWidget(group_label)
            for name, icon, cls in page_classes:
                page = cls(user)
                self.stack.addWidget(page)
                btn = QPushButton(f'{icon}  {name}'); btn.setCheckable(True)
                btn.clicked.connect(lambda checked=False, idx=len(self.pages), n=name: self.switch_page(idx, n))
                if not can_access(user['role'], name):
                    btn.setEnabled(False)
                    btn.setToolTip('当前角色无权限访问此模块')
                self.nav_buttons_layout.addWidget(btn)
                self.pages.append((name, page, btn))
        self.nav_buttons_layout.addStretch()
        logout = ghost(QPushButton('退出登录')); logout.clicked.connect(self.close)
        nav_layout.addWidget(logout)
        main.addWidget(self.nav); main.addWidget(shell, 1)
        for i, (n, _, b) in enumerate(self.pages):
            if b.isEnabled(): self.switch_page(i, n); break

    def switch_by_name(self, name: str):
        for idx, (n, _, btn) in enumerate(self.pages):
            if n == name:
                self.switch_page(idx, n)
                return

    def switch_page(self, idx: int, name: str):
        if not self.pages[idx][2].isEnabled():
            QMessageBox.warning(self, '权限不足', '当前角色无权访问该功能。')
            return
        for _, _, btn in self.pages: btn.setChecked(False)
        self.pages[idx][2].setChecked(True)
        self.stack.setCurrentIndex(idx)
        self.page_title.setText(name)
        hints = {
            '数据集驾驶舱': '从交付视角看样本、标注、质检、返工和版本是否达标。',
            '样本标注生产工作台': '按风险优先处理预标注、人工修正、实时自检和返工说明。',
            '质量校验中心': '结合自动规则、人工复核和返工工作流处理高风险样本。',
            '训练格式导出中心': '执行交付前检查并导出 YOLO / COCO / VOC / JSONL。',
        }
        self.page_hint.setText(hints.get(name, '围绕 AI 训练样本生产、质量校验和数据集交付提供真实业务操作。'))
        page = self.pages[idx][1]
        if hasattr(page, 'refresh'): page.refresh()
