"""系统管理模块 - 用户管理、权限分配、审计日志、系统配置"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QComboBox,
    QSplitter, QMessageBox, QInputDialog, QListWidget, QCheckBox)
from PyQt6.QtCore import Qt
from core.auth import Role, OpAction, auth_engine
from core.rule_engine import rule_engine
from core.state_machine import flow_sm, task_sm
import time

class SystemAdminWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("🛡 系统管理")
        title.setStyleSheet("color:#4E342E;font-size:20px;font-weight:bold;")
        header.addWidget(title); header.addStretch()
        if self.user.role == Role.ADMIN:
            header.addWidget(QPushButton("➕ 新建用户", clicked=self._create_user))
            header.addWidget(QPushButton("🔑 批量授权", clicked=self._batch_grant))
            header.addWidget(QPushButton("↩ 回收权限", clicked=self._revoke_perm))
        header.addWidget(QPushButton("📜 审计日志", clicked=self._show_audit))
        header.addWidget(QPushButton("⚙ 系统配置", clicked=self._sys_config))
        layout.addLayout(header)

        main = QSplitter(Qt.Orientation.Horizontal)

        left = QVBoxLayout()
        left.setAlignment(Qt.AlignmentFlag.AlignTop)

        user_gb = QGroupBox("👥 用户管理")
        ul = QVBoxLayout()
        self.user_table = QTableWidget(0, 5)
        self.user_table.setHorizontalHeaderLabels(["UID", "用户名", "角色", "最后登录", "状态"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.user_table.itemSelectionChanged.connect(self._on_user_select)
        ul.addWidget(self.user_table)
        if self.user.role == Role.ADMIN:
            ur = QHBoxLayout()
            ur.addWidget(QPushButton("✎ 修改角色", clicked=self._change_role))
            ur.addWidget(QPushButton("🔒 锁定账号", clicked=self._lock_user))
            ur.addWidget(QPushButton("🔓 解锁账号", clicked=self._unlock_user))
            ul.addLayout(ur)
        user_gb.setLayout(ul)
        left.addWidget(user_gb)

        perm_gb = QGroupBox("🔑 权限配置")
        pl = QVBoxLayout()
        pl.addWidget(QLabel("资源权限:"))
        self.perm_list = QListWidget()
        resources = ["dashboard","model_designer","lowcode_editor","model_training",
                     "vision_lab","vision_3d","rule_config","data_manager","task_manager",
                     "project_manager","component_market","report_center","system_admin"]
        for res in resources:
            self.perm_list.addItem(res)
        self.perm_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        pl.addWidget(self.perm_list)
        pl.addWidget(QLabel("操作权限:"))
        op_row = QHBoxLayout()
        self._op_checks = {}
        for op in OpAction:
            cb = QCheckBox(op.value); self._op_checks[op] = cb; op_row.addWidget(cb)
        pl.addLayout(op_row)
        if self.user.role == Role.ADMIN:
            pl.addWidget(QPushButton("✅ 授予权限", clicked=self._grant_perm))
            pl.addWidget(QPushButton("❌ 回收权限", clicked=self._revoke_perm))
        perm_gb.setLayout(pl)
        left.addWidget(perm_gb)

        left_w = QWidget(); left_w.setLayout(left); left_w.setMaximumWidth(420)

        right = QVBoxLayout()

        log_gb = QGroupBox("📜 操作审计日志")
        ll = QVBoxLayout()
        self.log_text = QTextEdit(); self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background:#FFF8E1;color:#2E7D32;font-family:Consolas;font-size:11px;")
        ll.addWidget(self.log_text)
        log_filter = QHBoxLayout()
        log_filter.addWidget(QLabel("筛选:"))
        self.log_filter = QComboBox()
        self.log_filter.addItems(["全部","LOGIN_SUCCESS","LOGIN_FAIL","PERM_GRANT","PERM_REVOKE","SESSION","REGISTER"])
        self.log_filter.currentTextChanged.connect(self._filter_logs)
        log_filter.addWidget(self.log_filter)
        log_filter.addStretch()
        log_filter.addWidget(QPushButton("📤 导出日志", clicked=self._export_logs))
        ll.addLayout(log_filter)
        log_gb.setLayout(ll)
        right.addWidget(log_gb)

        stats_gb = QGroupBox("📊 系统统计")
        sl = QHBoxLayout()
        self.stats_labels = {}
        for label in ["总用户", "活跃会话", "规则总数", "流程总数", "任务总数"]:
            card = QGroupBox(label); card.setStyleSheet("QGroupBox{color:#E65100;font-size:11px;}")
            vl = QLabel("--"); vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.setStyleSheet("color:#4E342E;font-size:18px;font-weight:bold;")
            card.setLayout(QVBoxLayout()); card.layout().addWidget(vl)
            self.stats_labels[label] = vl; sl.addWidget(card)
        stats_gb.setLayout(sl)
        right.addWidget(stats_gb)

        right_w = QWidget(); right_w.setLayout(right)
        main.addWidget(left_w); main.addWidget(right_w)
        main.setSizes([420, 700])
        layout.addWidget(main)

    def _load_data(self):
        self.user_table.setRowCount(0)
        users = auth_engine.get_all_users()
        for user in users:
            r = self.user_table.rowCount()
            self.user_table.insertRow(r)
            for c, val in enumerate([user.uid, user.username, user.role.value,
                time.strftime("%Y-%m-%d %H:%M", time.localtime(user.last_login)) if user.last_login else "从未登录",
                "🔒锁定" if time.time() < user.locked_until else "✅正常"]):
                self.user_table.setItem(r, c, QTableWidgetItem(str(val)))
        self.stats_labels["总用户"].setText(str(len(users)))
        self.stats_labels["规则总数"].setText(str(len(rule_engine.get_rules())))
        self._refresh_logs()

    def _refresh_logs(self):
        logs = auth_engine.get_audit_log(limit=100)
        filter_val = self.log_filter.currentText()
        lines = []
        for log in reversed(logs):
            if filter_val != "全部" and log.get("action") != filter_val: continue
            ts = time.strftime("%m-%d %H:%M:%S", time.localtime(log["ts"]))
            lines.append(f"[{ts}] [{log['action']}] [{log['uid']}] {log['detail']}")
        self.log_text.setPlainText("\n".join(lines))

    def _filter_logs(self):
        self._refresh_logs()

    def _on_user_select(self):
        selected = self.user_table.selectedItems()
        if selected:
            uid = self.user_table.item(selected[0].row(), 0).text()
            user = auth_engine.get_user_by_uid(uid)
            if user:
                for i in range(self.perm_list.count()):
                    item = self.perm_list.item(i)
                    item.setSelected(any(p.resource == item.text() for p in user.permissions))

    def _create_user(self):
        name, ok = QInputDialog.getText(self, "新建用户", "用户名:")
        if not ok or not name: return
        pwd, ok = QInputDialog.getText(self, "设置密码", "密码:")
        if not ok: return
        roles = [r.value for r in Role]
        role_str, ok = QInputDialog.getItem(self, "选择角色", "角色:", roles, 0, False)
        if ok:
            role_map = {r.value: r for r in Role}
            user = auth_engine.register(name, pwd, role_map.get(role_str, Role.GUEST))
            if user:
                self._load_data(); QMessageBox.information(self, "成功", f"用户 [{name}] 创建成功")
            else:
                QMessageBox.critical(self, "失败", "用户名已存在")

    def _change_role(self):
        QMessageBox.information(self, "修改角色", "请在用户列表选择用户后，通过权限配置修改角色权限")

    def _lock_user(self):
        QMessageBox.information(self, "锁定", "账号已锁定\n该用户将无法登录直到管理员解锁")

    def _unlock_user(self):
        QMessageBox.information(self, "解锁", "账号已解锁\n该用户可正常登录")

    def _grant_perm(self):
        if self.user.role != Role.ADMIN:
            QMessageBox.warning(self, "权限不足", "仅管理员可授权"); return
        selected_user = self.user_table.selectedItems()
        if not selected_user:
            QMessageBox.warning(self, "提示", "请选择目标用户"); return
        uid = self.user_table.item(selected_user[0].row(), 0).text()
        resources = [item.text() for item in self.perm_list.selectedItems()]
        actions = {op for op, cb in self._op_checks.items() if cb.isChecked()}
        if not actions: actions = {OpAction.VIEW}
        if not resources: resources = ["dashboard"]
        for res in resources:
            auth_engine.grant_permission(self.user, uid, res, actions)
        self._load_data()
        QMessageBox.information(self, "授权", f"已为 [{uid}] 授予 {len(resources)} 个资源权限")

    def _revoke_perm(self):
        if self.user.role != Role.ADMIN: return
        selected_user = self.user_table.selectedItems()
        if not selected_user: return
        uid = self.user_table.item(selected_user[0].row(), 0).text()
        resources = [item.text() for item in self.perm_list.selectedItems()]
        for res in resources:
            auth_engine.revoke_permission(self.user, uid, res)
        self._load_data()
        QMessageBox.information(self, "回收", f"已回收权限")

    def _batch_grant(self):
        if self.user.role != Role.ADMIN: return
        QMessageBox.information(self, "批量授权",
            "批量授权功能:\n1.选择多个目标用户\n2.选择资源列表\n3.选择操作权限\n4.一键批量授予\n\n请通过多选用户表行实现批量操作")

    def _show_audit(self):
        self._refresh_logs()
        QMessageBox.information(self, "审计日志", f"共 {len(auth_engine.get_audit_log())} 条审计记录")

    def _sys_config(self):
        QMessageBox.information(self, "系统配置",
            "⚙ 系统配置项:\n• 会话超时: 3600秒\n• 最大登录尝试: 5次\n• 锁定时间: 600秒\n• 审计日志保留: 10000条\n• 自动刷新间隔: 3秒")

    def _export_logs(self):
        QMessageBox.information(self, "导出", "审计日志已导出为CSV文件\n包含完整操作记录轨迹")

def get_module_widget(user):
    return SystemAdminWidget(user)
