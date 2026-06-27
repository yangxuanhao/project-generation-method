"""数据管理模块 - 多源数据接入、交互式编辑、事务管理、快照与回溯"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QSplitter,
    QFileDialog, QMessageBox, QComboBox, QLineEdit, QListWidget)
from PyQt6.QtCore import Qt
from core.auth import Role, OpAction, auth_engine
from core.data_consistency import data_engine, DataTransaction
from core.algorithms import DataAdapter, FeatureAnalyzer, HashValidator
from core.rule_engine import rule_engine, TriggerType, Condition, CompareOp, RuleAction
import json, csv, io

class DataManagerWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user; self._current_data = []; self._flow_id = "data_flow_1"
        self._txn = None
        data_engine.register_node(self._flow_id, "main", [])
        data_engine.add_integrity_rule(lambda k, d: isinstance(d, (list, dict)))
        self._setup_ui(); self._init_demo_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("💾 数据管理中心")
        title.setStyleSheet("color:#4E342E;font-size:20px;font-weight:bold;")
        header.addWidget(title); header.addStretch()
        import_btns = [
            ("📂 CSV", self._import_csv), ("📂 JSON", self._import_json),
            ("📂 TXT", self._import_txt), ("🖼 图片", self._import_image),
            ("📤 导出", self._export_data), ("🔍 分析", self._analyze_data),
        ]
        for label, handler in import_btns:
            header.addWidget(QPushButton(label, clicked=handler))
        layout.addLayout(header)

        main = QSplitter(Qt.Orientation.Horizontal)

        left = QVBoxLayout()
        left.setAlignment(Qt.AlignmentFlag.AlignTop)

        snap_gb = QGroupBox("📸 数据快照管理")
        sl = QVBoxLayout()
        self.snap_list = QListWidget()
        self.snap_list.itemClicked.connect(self._load_snapshot)
        sl.addWidget(self.snap_list)
        snap_btns = QHBoxLayout()
        snap_btns.addWidget(QPushButton("💾 创建快照", clicked=self._create_snapshot))
        snap_btns.addWidget(QPushButton("↩ 回溯", clicked=self._restore_snapshot))
        sl.addLayout(snap_btns)
        snap_gb.setLayout(sl)
        left.addWidget(snap_gb)

        txn_gb = QGroupBox("🔄 事务管理")
        tl = QVBoxLayout()
        self.txn_status = QLabel("事务状态: 无活动事务")
        self.txn_status.setStyleSheet("color:#795548;")
        tl.addWidget(self.txn_status)
        txn_btns = QHBoxLayout()
        txn_btns.addWidget(QPushButton("▶ 开始事务", clicked=self._begin_txn))
        txn_btns.addWidget(QPushButton("✓ 提交", clicked=self._commit_txn))
        txn_btns.addWidget(QPushButton("↩ 回滚", clicked=self._rollback_txn))
        tl.addLayout(txn_btns)
        txn_gb.setLayout(tl)
        left.addWidget(txn_gb)

        filter_gb = QGroupBox("🔍 数据筛选")
        fl = QVBoxLayout()
        fl.addWidget(QLabel("筛选条件 (字段:值):"))
        self.filter_input = QLineEdit(""); fl.addWidget(self.filter_input)
        fl.addWidget(QPushButton("🔍 执行筛选", clicked=self._filter_data))
        fl.addWidget(QPushButton("🔄 清除筛选", clicked=self._clear_filter))
        filter_gb.setLayout(fl)
        left.addWidget(filter_gb)

        left_w = QWidget(); left_w.setLayout(left); left_w.setMaximumWidth(250)

        right = QVBoxLayout()
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.itemChanged.connect(self._on_cell_edit)
        right.addWidget(QLabel("📊 数据表格（支持直接编辑单元格）", styleSheet="color:#E65100;font-weight:bold;"))
        right.addWidget(self.data_table)

        self.stats_text = QTextEdit(); self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(100)
        self.stats_text.setStyleSheet("background:#FFF8E1;color:#4E342E;font-family:Consolas;font-size:11px;")
        right.addWidget(QLabel("📋 数据统计与校验:", styleSheet="color:#E65100;"))
        right.addWidget(self.stats_text)

        right_w = QWidget(); right_w.setLayout(right)
        main.addWidget(left_w); main.addWidget(right_w)
        main.setSizes([250, 950])
        layout.addWidget(main)

    def _init_demo_data(self):
        self._current_data = [
            {"id": 1, "feature_a": 5.1, "feature_b": 3.5, "feature_c": 1.4, "label": "A"},
            {"id": 2, "feature_a": 4.9, "feature_b": 3.0, "feature_c": 1.4, "label": "A"},
            {"id": 3, "feature_a": 7.0, "feature_b": 3.2, "feature_c": 4.7, "label": "B"},
            {"id": 4, "feature_a": 6.4, "feature_b": 3.2, "feature_c": 4.5, "label": "B"},
            {"id": 5, "feature_a": 5.5, "feature_b": 2.3, "feature_c": 4.0, "label": "B"},
            {"id": 6, "feature_a": 6.3, "feature_b": 3.3, "feature_c": 6.0, "label": "C"},
            {"id": 7, "feature_a": 5.8, "feature_b": 2.7, "feature_c": 5.1, "label": "C"},
            {"id": 8, "feature_a": 7.1, "feature_b": 3.0, "feature_c": 5.9, "label": "C"},
        ]
        self._refresh_table()
        self.stats_text.setPlainText(f"演示数据集 | {len(self._current_data)} 条 | 校验: {HashValidator.checksum(self._current_data)}")

    def _refresh_table(self, data: list = None):
        if data is not None: self._current_data = data
        d = self._current_data
        if not d: return
        headers = list(d[0].keys())
        self.data_table.setColumnCount(len(headers))
        self.data_table.setHorizontalHeaderLabels(headers)
        self.data_table.setRowCount(len(d))
        for r, row in enumerate(d):
            for c, key in enumerate(headers):
                self.data_table.setItem(r, c, QTableWidgetItem(str(row.get(key, ""))))
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def _on_cell_edit(self, item):
        if not self._txn:
            self._begin_txn()
        row, col = item.row(), item.column()
        key = self.data_table.horizontalHeaderItem(col).text()
        try:
            val = eval(item.text())
        except:
            val = item.text()
        if row < len(self._current_data):
            self._current_data[row][key] = val
            if self._txn:
                data_engine.write(self._txn, "main", self._current_data)

    def _begin_txn(self):
        self._txn = data_engine.begin_transaction(self._flow_id)
        self.txn_status.setText(f"事务状态: 活跃 [{self._txn.txn_id[:8]}]")
        self.txn_status.setStyleSheet("color:#F57F17;")

    def _commit_txn(self):
        if self._txn and data_engine.commit(self._txn):
            self.txn_status.setText("事务状态: 已提交 ✓"); self.txn_status.setStyleSheet("color:#2E7D32;")
            self._txn = None
            self.stats_text.setPlainText(f"已提交 | 校验: {HashValidator.checksum(self._current_data)}")

    def _rollback_txn(self):
        if self._txn:
            old_data = data_engine.get_snapshot(self._flow_id, "main")
            if old_data:
                self._current_data = old_data; self._refresh_table()
            data_engine.rollback(self._txn)
            self.txn_status.setText("事务状态: 已回滚 ↩"); self.txn_status.setStyleSheet("color:#D84315;")
            self._txn = None

    def _create_snapshot(self):
        data_engine.register_node(self._flow_id, f"snap_{len(self.snap_list)}", self._current_data)
        ver = data_engine._data_store.get(f"{self._flow_id}:main", {}).get("version", 0)
        self.snap_list.addItem(f"快照 v{ver} - {len(self._current_data)}条")
        QMessageBox.information(self, "快照", f"快照已创建 v{ver}")

    def _load_snapshot(self, item):
        data = data_engine.get_snapshot(self._flow_id, "main")
        if data:
            self._current_data = data; self._refresh_table()

    def _restore_snapshot(self):
        data = data_engine.get_snapshot(self._flow_id, "main")
        if data:
            self._current_data = data; self._refresh_table()
            QMessageBox.information(self, "回溯", "已回溯到最近快照")
        else:
            QMessageBox.warning(self, "提示", "没有可用快照")

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入CSV", "", "CSV (*.csv);;所有 (*.*)")
        if path:
            self._current_data = DataAdapter.from_csv(path); self._refresh_table()

    def _import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入JSON", "", "JSON (*.json);;所有 (*.*)")
        if path:
            data = DataAdapter.from_json(path)
            if isinstance(data, list): self._current_data = data; self._refresh_table()

    def _import_txt(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入TXT", "", "TXT (*.txt);;所有 (*.*)")
        if path:
            with open(path, 'r', encoding='utf-8') as f: content = f.read()
            self._current_data = [{"line": i+1, "content": l} for i, l in enumerate(content.split('\n')[:50]) if l.strip()]
            self._refresh_table()

    def _import_image(self):
        QMessageBox.information(self, "导入图片", "图片数据请使用视觉实验室模块导入处理")

    def _export_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出数据", "data.csv", "CSV (*.csv);;JSON (*.json)")
        if path:
            if path.endswith('.json'):
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self._current_data, f, ensure_ascii=False, indent=2)
            else:
                with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=self._current_data[0].keys())
                    w.writeheader(); w.writerows(self._current_data)
            QMessageBox.information(self, "导出", f"数据已导出至 {path}")

    def _analyze_data(self):
        if self._current_data:
            analysis = FeatureAnalyzer.analyze(self._current_data)
            self.stats_text.setPlainText(json.dumps(analysis, ensure_ascii=False, indent=2))

    def _filter_data(self):
        cond = self.filter_input.text().strip()
        if not cond: return
        try:
            field, value = cond.split(':', 1)
            filtered = [row for row in self._current_data if str(row.get(field.strip(), '')) == value.strip()]
            self._refresh_table(filtered)
        except: pass

    def _clear_filter(self):
        self._refresh_table()

def get_module_widget(user):
    return DataManagerWidget(user)
