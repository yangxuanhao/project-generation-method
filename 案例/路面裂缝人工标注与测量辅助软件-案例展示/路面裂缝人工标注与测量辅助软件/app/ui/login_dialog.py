from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox, QFrame
from PyQt6.QtCore import Qt
from app.core.storage import StorageManager
from app.core.models import User


class LoginDialog(QDialog):
    def __init__(self, storage: StorageManager):
        super().__init__()
        self.storage = storage
        self.current_user: User | None = None
        self.setWindowTitle("路面裂缝人工标注与测量辅助软件 - 登录")
        self.resize(440, 360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(14)
        title = QLabel("路面裂缝人工标注与测量辅助软件")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("裂缝标注 · 卡尺测量 · 复核纠偏 · 修复估算")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.username = QLineEdit("admin")
        self.username.setPlaceholderText("用户名")
        self.password = QLineEdit("admin123")
        self.password.setPlaceholderText("密码")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.role = QComboBox()
        self.role.addItems(["标注员", "复核员", "管理员"])
        layout.addWidget(QLabel("用户名"))
        layout.addWidget(self.username)
        layout.addWidget(QLabel("密码"))
        layout.addWidget(self.password)
        layout.addWidget(QLabel("注册角色"))
        layout.addWidget(self.role)

        row = QHBoxLayout()
        login_btn = QPushButton("登录")
        login_btn.setObjectName("PrimaryButton")
        reg_btn = QPushButton("注册新账号")
        row.addWidget(login_btn)
        row.addWidget(reg_btn)
        layout.addLayout(row)
        tips = QLabel("默认账号：admin / admin123。注册后可直接登录。")
        tips.setWordWrap(True)
        tips.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tips)
        login_btn.clicked.connect(self.login)
        reg_btn.clicked.connect(self.register)

    def login(self):
        user = self.storage.verify_user(self.username.text(), self.password.text())
        if not user:
            QMessageBox.warning(self, "登录失败", "用户名或密码不正确")
            return
        self.current_user = user
        self.accept()

    def register(self):
        ok, msg = self.storage.register_user(self.username.text(), self.password.text(), self.role.currentText())
        if ok:
            QMessageBox.information(self, "注册成功", msg + "，现在可以登录。")
        else:
            QMessageBox.warning(self, "注册失败", msg)
