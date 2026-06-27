"""任务管控模块 - 任务队列管理、运行日志、异常处理、优先级调度"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QSpinBox,
    QComboBox, QSplitter, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from core.auth import Role, OpAction, auth_engine
from core.state_machine import task_sm, TaskState, flow_sm, FlowState
from core.rule_engine import rule_engine, TriggerType
import time, uuid

class TaskManagerWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user; self._tasks = []
        self._log_buffer = []; self._error_buffer = []
        self._setup_ui(); self._init_demo_tasks()
        self._timer = QTimer(self); self._timer.timeout.connect(self._refresh)
        self._timer.start(2000)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("📋 任务管控中心")
        title.setStyleSheet("color:#4E342E;font-size:20px;font-weight:bold;")
        header.addWidget(title); header.addStretch()
        header.addWidget(QPushButton("➕ 创建任务", clicked=self._create_task))
        header.addWidget(QPushButton("⏸ 暂停全部", clicked=self._pause_all))
        header.addWidget(QPushButton("▶ 恢复全部", clicked=self._resume_all))
        header.addWidget(QPushButton("⏹ 终止选中", clicked=self._terminate_selected))
        header.addWidget(QPushButton("🗑 清理已完成", clicked=self._clean_completed))
        layout.addLayout(header)

        main = QSplitter(Qt.Orientation.Horizontal)

        left = QVBoxLayout()
        left.setAlignment(Qt.AlignmentFlag.AlignTop)

        ctrl_gb = QGroupBox("⚙ 新建任务")
        cl = QVBoxLayout()
        cl.addWidget(QLabel("任务类型:"))
        self.task_type = QComboBox()
        self.task_type.addItems(["模型训练", "数据预处理", "模型推理", "批量处理", "模型导出", "报表生成", "数据校验"])
        cl.addWidget(self.task_type)
        cl.addWidget(QLabel("优先级 (1-10):"))
        self.task_priority = QSpinBox(); self.task_priority.setRange(1, 10); self.task_priority.setValue(5)
        cl.addWidget(self.task_priority)
        cl.addWidget(QPushButton("✅ 确认创建", clicked=self._create_task))
        ctrl_gb.setLayout(cl)
        left.addWidget(ctrl_gb)

        stats_gb = QGroupBox("📊 任务统计")
        sl = QVBoxLayout()
        self.stats_label = QLabel("排队:0 | 执行:0 | 完成:0 | 失败:0")
        self.stats_label.setStyleSheet("color:#795548;")
        sl.addWidget(self.stats_label)
        stats_gb.setLayout(sl)
        left.addWidget(stats_gb)
        left.addStretch()

        left_w = QWidget(); left_w.setLayout(left); left_w.setMaximumWidth(240)

        right = QVBoxLayout()
        right.addWidget(QLabel("📋 任务队列", styleSheet="color:#E65100;font-weight:bold;"))
        self.task_table = QTableWidget(0, 6)
        self.task_table.setHorizontalHeaderLabels(["任务ID", "类型", "状态", "优先级", "创建时间", "错误信息"])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right.addWidget(self.task_table)

        log_split = QSplitter(Qt.Orientation.Vertical)
        log_gb = QGroupBox("📜 运行日志")
        ll = QVBoxLayout()
        self.log_text = QTextEdit(); self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background:#FFF8E1;color:#2E7D32;font-family:Consolas;font-size:11px;")
        ll.addWidget(self.log_text)
        log_gb.setLayout(ll)

        err_gb = QGroupBox("❌ 异常日志 & 修复指引")
        el = QVBoxLayout()
        self.error_text = QTextEdit(); self.error_text.setReadOnly(True)
        self.error_text.setStyleSheet("background:#FFF8E1;color:#D84315;font-family:Consolas;font-size:11px;")
        el.addWidget(self.error_text)
        el.addWidget(QPushButton("🔧 异常修复指引", clicked=self._show_repair_guide))
        err_gb.setLayout(el)

        log_split.addWidget(log_gb); log_split.addWidget(err_gb)
        right.addWidget(log_split)

        right_w = QWidget(); right_w.setLayout(right)
        main.addWidget(left_w); main.addWidget(right_w)
        main.setSizes([240, 900])
        layout.addWidget(main)

    def _init_demo_tasks(self):
        demo_tasks = [
            ("T001", "模型训练", [TaskState.PREPARING, TaskState.EXECUTING], 8),
            ("T002", "数据预处理", [TaskState.PREPARING], 6),
            ("T003", "模型推理", [], 9),
            ("T004", "批量处理", [TaskState.PREPARING, TaskState.EXECUTING, TaskState.COMPLETED], 4),
            ("T005", "模型导出", [TaskState.PREPARING, TaskState.EXECUTING, TaskState.FAILED], 7),
            ("T006", "报表生成", [TaskState.PREPARING, TaskState.EXECUTING, TaskState.PAUSED], 3),
        ]
        for tid, ttype, transitions, priority in demo_tasks:
            task_sm.create_task(tid, ttype, priority)
            for target_state in transitions:
                task_sm.transition(tid, target_state)
            t = task_sm._tasks.get(tid)
            if t and t["state"] in (TaskState.FAILED,):
                t["error"] = "模拟异常: 数据格式校验失败"
        self._log("系统", "任务队列初始化完成（6个演示任务）", "INFO")
        self._refresh()

    def _create_task(self):
        if not auth_engine.check_permission(self.user, "task_manager", OpAction.CREATE):
            QMessageBox.warning(self, "权限不足", "无创建任务权限"); return
        tid = f"T{uuid.uuid4().hex[:6]}"
        task_sm.create_task(tid, self.task_type.currentText(), self.task_priority.value())
        self._log(tid, f"任务创建: {self.task_type.currentText()} 优先级:{self.task_priority.value()}", "CREATE")
        self._refresh()

    def _pause_all(self):
        self._log("SYSTEM", "暂停所有执行中任务", "PAUSE")

    def _resume_all(self):
        self._log("SYSTEM", "恢复所有暂停任务", "RESUME")

    def _terminate_selected(self):
        selected = self.task_table.selectedItems()
        if selected:
            tid = self.task_table.item(selected[0].row(), 0).text()
            task_sm.transition(tid, TaskState.CANCELLED)
            self._log(tid, "任务强制终止", "TERMINATE")
            self._refresh()

    def _clean_completed(self):
        self._log("SYSTEM", "清理已完成/已取消任务", "CLEAN")

    def _refresh(self):
        tasks = task_sm.get_all_tasks()
        self.task_table.setRowCount(0)
        counts = {s: 0 for s in TaskState}
        for t in tasks:
            state = t["state"]
            if isinstance(state, TaskState):
                state_str = state.value
                counts[state] = counts.get(state, 0) + 1
            else:
                state_str = str(state)
            r = self.task_table.rowCount()
            self.task_table.insertRow(r)
            created_ts = t.get("created", 0)
            created_str = time.strftime("%H:%M:%S", time.localtime(created_ts)) if created_ts else "--"
            for c, val in enumerate([t["id"], t["type"], state_str,
                str(t["priority"]), created_str, t.get("error", "") or ""]):
                self.task_table.setItem(r, c, QTableWidgetItem(str(val)))
        all_states = [
            ("排队", TaskState.QUEUED), ("准备", TaskState.PREPARING),
            ("执行", TaskState.EXECUTING), ("暂停", TaskState.PAUSED),
            ("完成", TaskState.COMPLETED), ("失败", TaskState.FAILED),
            ("取消", TaskState.CANCELLED),
        ]
        parts = [f"{label}:{counts.get(state, 0)}" for label, state in all_states]
        self.stats_label.setText(" | ".join(parts))

    def _log(self, tid: str, msg: str, level: str = "INFO"):
        ts = time.strftime("%H:%M:%S")
        self._log_buffer.append(f"[{ts}][{level}][{tid}] {msg}")
        if level in ("ERROR", "FATAL"):
            self._error_buffer.append(f"[{ts}][{level}][{tid}] {msg}")
        # 保持缓冲区
        if len(self._log_buffer) > 200: self._log_buffer = self._log_buffer[-200:]
        self.log_text.setPlainText("\n".join(self._log_buffer[-50:]))
        self.error_text.setPlainText("\n".join(self._error_buffer[-20:]))

    def _show_repair_guide(self):
        guides = {
            "模型加载异常": "1.检查模型文件路径\n2.验证模型格式兼容性\n3.查看依赖库版本",
            "数据异常": "1.检查数据格式是否正确\n2.验证缺失值处理\n3.确认编码格式",
            "内存不足": "1.减少批次大小\n2.降低输入维度\n3.使用数据生成器",
        }
        msgs = "\n\n".join([f"【{k}】\n{v}" for k, v in guides.items()])
        QMessageBox.information(self, "异常修复指引", msgs)

def get_module_widget(user):
    return TaskManagerWidget(user)
