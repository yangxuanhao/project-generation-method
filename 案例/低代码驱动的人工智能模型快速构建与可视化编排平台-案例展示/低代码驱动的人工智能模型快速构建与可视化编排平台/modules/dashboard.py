"""工作台 - 项目总览、快速导航、最近项目、模板入口"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QListWidget, QScrollArea, QGroupBox, QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from core.auth import Role, OpAction, auth_engine
from core.state_machine import FlowState, flow_sm, task_sm, TaskState
from core.rule_engine import rule_engine, TriggerType
import time, random

class DashboardWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("📊 工作台")
        title.setStyleSheet("color:#4E342E;font-size:24px;font-weight:bold;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        stats_row = QHBoxLayout()
        stats = [
            ("📋 总项目数", "5", "#1565C0"),
            ("⚡ 运行中", "2", "#2E7D32"),
            ("⏸ 暂停", "1", "#E65100"),
            ("✅ 已完成", "12", "#0277BD"),
            ("❌ 异常", "0", "#C62828"),
            ("📜 规则数", "8", "#6A1B9A"),
        ]
        for label, value, color in stats:
            card = QFrame()
            card.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #FFFFFF,stop:1 #FFF8E1);border:1px solid #FFD54F;border-radius:10px;padding:12px;")
            card.setFixedHeight(100)
            cl = QVBoxLayout(card)
            vl = QLabel(value); vl.setStyleSheet(f"color:{color};font-size:36px;font-weight:bold;")
            vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ll = QLabel(label); ll.setStyleSheet("color:#5D4037;font-size:12px;font-weight:bold;")
            ll.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(vl); cl.addWidget(ll)
            stats_row.addWidget(card)
        layout.addLayout(stats_row)

        main_row = QHBoxLayout()

        left_panel = QVBoxLayout()
        tmpl_gb = QGroupBox("🚀 AI模型模板 - 一键新建项目")
        tmpl_gb.setStyleSheet("QGroupBox{color:#E65100;font-weight:bold;font-size:14px;}")
        tmpl_grid = QGridLayout()
        templates = [
            ("🔢 分类模型", "支持二分类/多分类任务，预置RF/SVM/MLP"), ("📈 回归模型", "线性回归/多项式回归/梯度提升回归"),
            ("🎯 目标检测", "YOLO架构/SSD/区域提议检测"), ("🖼 图像分割", "U-Net/DeepLab/语义分割"),
            ("📝 文本分析", "NLP情感分析/实体识别/文本分类"), ("⏱ 时序预测", "LSTM/Prophet/ARIMA时序预测"),
        ]
        for i, (name, desc) in enumerate(templates):
            btn = QPushButton(f"{name}\n{desc}")
            btn.setMinimumHeight(70); btn.setStyleSheet("text-align:left;padding:12px;")
            btn.clicked.connect(lambda checked, n=name: self._create_from_template(n))
            tmpl_grid.addWidget(btn, i // 3, i % 3)
        tmpl_gb.setLayout(tmpl_grid)
        left_panel.addWidget(tmpl_gb)

        recent_gb = QGroupBox("📁 最近项目")
        self.recent_list = QListWidget()
        left_panel.addWidget(recent_gb)
        left_panel.addWidget(self.recent_list)

        right_panel = QVBoxLayout()

        flow_gb = QGroupBox("🔄 流程状态监控")
        self.flow_list = QListWidget()
        flow_gb.setLayout(QVBoxLayout())
        flow_gb.layout().addWidget(self.flow_list)
        right_panel.addWidget(flow_gb)

        task_gb = QGroupBox("📋 任务队列")
        self.task_list = QListWidget()
        task_gb.setLayout(QVBoxLayout())
        task_gb.layout().addWidget(self.task_list)
        right_panel.addWidget(task_gb)

        alert_gb = QGroupBox("🔔 系统通知")
        self.alert_list = QListWidget()
        alert_gb.setLayout(QVBoxLayout())
        alert_gb.layout().addWidget(self.alert_list)
        right_panel.addWidget(alert_gb)

        main_row.addLayout(left_panel, 3)
        main_row.addLayout(right_panel, 2)
        layout.addLayout(main_row)

    def _load_data(self):
        projects = [("图像分类项目-v3", "运行态", "2024-06-12"), ("目标检测项目", "编辑态", "2024-06-11"),
                    ("文本情感分析", "已完成", "2024-06-10"), ("时序销售预测", "暂停态", "2024-06-09"),
                    ("3D点云分割", "调试态", "2024-06-08")]
        for name, state, date in projects:
            self.recent_list.addItem(f"  {name}  [{state}]  {date}")

        flows = [("图像分类流程", "运行态"), ("目标检测流程", "编辑态"), ("文本分析流程", "已完成"),
                 ("3D点云流程", "暂停态"), ("时序预测流程", "调试态")]
        for name, state in flows:
            self.flow_list.addItem(f"  {name}  → {state}")

        tasks = [("训练-图像分类v3", "执行中 65%"), ("推理-目标检测", "排队中 优先级8"),
                 ("数据预处理-时序", "已完成"), ("模型导出-YOLO", "排队中")]
        for name, status in tasks:
            self.task_list.addItem(f"  {name} [{status}]")

        alerts = ["✅ 规则冲突检测: 0个冲突", "⚠ 磁盘空间剩余: 45.2GB", "ℹ 今日已执行任务: 23个",
                  "🔒 权限变更: admin授权了operator"]
        for alert in alerts:
            self.alert_list.addItem(f"  {alert}")

    def _create_from_template(self, tmpl_name: str):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "新建项目", f"基于模板 [{tmpl_name}] 创建新项目\n请在模型设计器中开始编排流程。")

def get_module_widget(user):
    return DashboardWidget(user)
