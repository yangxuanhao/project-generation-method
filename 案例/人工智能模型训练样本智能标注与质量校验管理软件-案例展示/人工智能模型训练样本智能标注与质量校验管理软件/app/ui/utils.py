from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QMessageBox, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


SEVERITY_ORDER = {'高': 3, '中': 2, '低': 1}


def page_root(title: str, subtitle: str | None = None, show_header: bool = False) -> tuple[QWidget, QVBoxLayout]:
    root = QWidget()
    root.setObjectName('pageRoot')
    layout = QVBoxLayout(root)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(12)
    if show_header:
        header = QHBoxLayout()
        title_box = QVBoxLayout(); title_box.setSpacing(3)
        lab = QLabel(title)
        lab.setProperty('pageTitle', True)
        title_box.addWidget(lab)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setProperty('pageSubtitle', True)
            sub.setWordWrap(True)
            title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)
    return root, layout


def card(object_name: str | None = None) -> QFrame:
    f = QFrame()
    f.setProperty('card', True)
    if object_name:
        f.setObjectName(object_name)
    f.setFrameShape(QFrame.Shape.NoFrame)
    return f


def glass_card() -> QFrame:
    f = card()
    f.setProperty('glass', True)
    return f


def secondary(btn: QPushButton) -> QPushButton:
    btn.setProperty('secondary', True)
    return btn


def ghost(btn: QPushButton) -> QPushButton:
    btn.setProperty('ghost', True)
    return btn


def danger(btn: QPushButton) -> QPushButton:
    btn.setProperty('danger', True)
    return btn


def success(btn: QPushButton) -> QPushButton:
    btn.setProperty('success', True)
    return btn


def pill(text: str, tone: str = 'info') -> QLabel:
    label = QLabel(text)
    label.setProperty('pill', tone)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setMinimumHeight(24)
    return label


def title_label(text: str, subtitle: str | None = None) -> QWidget:
    box = QWidget(); lay = QVBoxLayout(box); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(2)
    t = QLabel(text); t.setProperty('sectionTitle', True); lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle); s.setProperty('sectionSubtitle', True); s.setWordWrap(True); lay.addWidget(s)
    return box


def fill_table(table: QTableWidget, rows: list[dict], columns: list[tuple[str, str]]):
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels([c[1] for c in columns])
    table.setRowCount(len(rows))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setSortingEnabled(False)
    for r, row in enumerate(rows):
        for c, (key, _) in enumerate(columns):
            v = row.get(key, '')
            item = QTableWidgetItem(str(v))
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            if key in ('severity', 'risk', 'status', 'qc_status'):
                text = str(v)
                if '高' in text or '退回' in text or '异常' in text:
                    item.setForeground(QColor('#b91c1c'))
                elif '中' in text or '待' in text or '返工' in text:
                    item.setForeground(QColor('#b45309'))
                elif '通过' in text or '完成' in text or '已保存' in text:
                    item.setForeground(QColor('#047857'))
            table.setItem(r, c, item)
    table.resizeRowsToContents()


def toast(parent: QWidget, title: str, text: str):
    QMessageBox.information(parent, title, text)


def make_project_combo(projects: list[dict]) -> QComboBox:
    combo = QComboBox()
    combo.setMinimumWidth(320)
    for p in projects:
        combo.addItem(f"{p['code']}｜{p['name']}", p['id'])
    return combo


def attach_page(widget: QWidget, root: QWidget):
    wrap = QVBoxLayout(widget)
    wrap.setContentsMargins(0, 0, 0, 0)
    wrap.addWidget(root)


def add_stretchy_label(layout, text: str):
    lab = QLabel(text); lab.setWordWrap(True); lab.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred); layout.addWidget(lab); return lab
