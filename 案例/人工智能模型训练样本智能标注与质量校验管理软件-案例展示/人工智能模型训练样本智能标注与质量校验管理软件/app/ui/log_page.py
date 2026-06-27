from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QLineEdit, QLabel
from app.ui.utils import page_root, fill_table, secondary
from app.core.database import fetch_all


class LogPage(QWidget):
    def __init__(self, user: dict):
        super().__init__(); self.user=user
        root,self.layout=page_root('操作日志')
        wrap=QVBoxLayout(self); wrap.setContentsMargins(0,0,0,0); wrap.addWidget(root)
        bar=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText('输入用户名、动作或关键字筛选日志')
        btn=QPushButton('搜索'); btn.clicked.connect(self.refresh)
        clear=secondary(QPushButton('清空筛选')); clear.clicked.connect(lambda:(self.search.setText(''),self.refresh()))
        bar.addWidget(QLabel('关键字')); bar.addWidget(self.search,2); bar.addWidget(btn); bar.addWidget(clear); bar.addStretch(); self.layout.addLayout(bar)
        self.table=QTableWidget(); self.layout.addWidget(self.table,1)

    def refresh(self):
        kw=self.search.text().strip()
        if kw:
            rows=fetch_all("SELECT * FROM operation_logs WHERE username LIKE ? OR action LIKE ? OR detail LIKE ? ORDER BY id DESC LIMIT 300", (f'%{kw}%',f'%{kw}%',f'%{kw}%'))
        else:
            rows=fetch_all('SELECT * FROM operation_logs ORDER BY id DESC LIMIT 300')
        fill_table(self.table, rows, [('username','用户'),('action','动作'),('detail','详情'),('created_at','时间')])
