from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame,
    QMessageBox, QDialog, QComboBox, QFormLayout
)
from PyQt6.QtCore import Qt
from app.core.config import APP_NAME
from app.core.database import fetch_one, execute, log_action
from app.ui.main_window import MainWindow


class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('注册新账号')
        self.setFixedSize(430, 420)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        title = QLabel('注册新账号')
        title.setStyleSheet('font-size:22px;font-weight:900;color:#0f172a;')
        desc = QLabel('用于本地演示环境。注册后默认启用，可立即登录系统。')
        desc.setWordWrap(True)
        desc.setStyleSheet('color:#64748b;')
        root.addWidget(title)
        root.addWidget(desc)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.username = QLineEdit()
        self.username.setPlaceholderText('4-20 位字母、数字或下划线')
        self.display_name = QLineEdit()
        self.display_name.setPlaceholderText('例如：标注员B')
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText('至少 6 位')
        self.password2 = QLineEdit()
        self.password2.setEchoMode(QLineEdit.EchoMode.Password)
        self.role = QComboBox()
        self.role.addItems(['标注员', '质检员', '项目经理'])
        form.addRow('用户名', self.username)
        form.addRow('显示名', self.display_name)
        form.addRow('密码', self.password)
        form.addRow('确认密码', self.password2)
        form.addRow('角色', self.role)
        root.addLayout(form)

        tip = QLabel('提示：管理员账号仍使用 admin / admin123。普通用户注册后只能访问其角色权限内页面。')
        tip.setWordWrap(True)
        tip.setStyleSheet('background:#eff6ff;color:#1d4ed8;border-radius:10px;padding:8px;')
        root.addWidget(tip)

        btns = QHBoxLayout()
        cancel = QPushButton('取消')
        cancel.setProperty('secondary', True)
        cancel.clicked.connect(self.reject)
        ok = QPushButton('完成注册')
        ok.clicked.connect(self.register)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(ok)
        root.addLayout(btns)

    def register(self):
        username = self.username.text().strip()
        display = self.display_name.text().strip() or username
        password = self.password.text()
        password2 = self.password2.text()
        if not username or len(username) < 4:
            QMessageBox.warning(self, '注册失败', '用户名至少需要 4 位。')
            return
        if not username.replace('_', '').isalnum():
            QMessageBox.warning(self, '注册失败', '用户名只能包含字母、数字或下划线。')
            return
        if len(password) < 6:
            QMessageBox.warning(self, '注册失败', '密码至少需要 6 位。')
            return
        if password != password2:
            QMessageBox.warning(self, '注册失败', '两次输入的密码不一致。')
            return
        if fetch_one('SELECT id FROM users WHERE username=?', (username,)):
            QMessageBox.warning(self, '注册失败', '用户名已存在，请换一个用户名。')
            return
        execute('INSERT INTO users(username,password,display_name,role,enabled) VALUES(?,?,?,?,1)', (username, password, display, self.role.currentText()))
        log_action(username, '注册账号', f'角色：{self.role.currentText()}')
        QMessageBox.information(self, '注册成功', f'账号 {username} 已创建，可以直接登录。')
        self.accept()


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(960, 600)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        left = QFrame(); left.setStyleSheet('background:#0f172a;color:white;')
        lyt = QVBoxLayout(left); lyt.setContentsMargins(42, 40, 42, 40)
        title = QLabel(APP_NAME); title.setWordWrap(True); title.setStyleSheet('font-size:28px;font-weight:900;color:white;line-height:1.4;')
        sub = QLabel('AI 训练样本入库、智能预标注、人工修正、自动质检、返工闭环、版本交付一体化桌面平台')
        sub.setWordWrap(True); sub.setStyleSheet('font-size:15px;color:#cbd5e1;')
        stats = QLabel('内置演示：安全帽/交通/工业缺陷图像数据集，客服、金融、医疗等文本数据集\n支持 YOLO、COCO、Pascal VOC、CSV、JSONL 导出')
        stats.setWordWrap(True); stats.setStyleSheet('color:#93c5fd;margin-top:20px;')
        lyt.addWidget(title); lyt.addWidget(sub); lyt.addSpacing(30); lyt.addWidget(stats); lyt.addStretch()
        card = QFrame(); card.setProperty('card', True); card.setFixedWidth(380)
        form = QVBoxLayout(card); form.setContentsMargins(30, 32, 30, 30)
        h = QLabel('登录系统'); h.setStyleSheet('font-size:24px;font-weight:800;color:#0f172a;')
        self.username = QLineEdit('admin'); self.username.setPlaceholderText('用户名')
        self.password = QLineEdit('admin123'); self.password.setPlaceholderText('密码'); self.password.setEchoMode(QLineEdit.EchoMode.Password)
        tip = QLabel('可用：admin/admin123、labeler/123456、reviewer/123456、manager/123456，也可以注册新账号。')
        tip.setWordWrap(True); tip.setStyleSheet('color:#64748b;')
        btn = QPushButton('登录并进入生产平台'); btn.clicked.connect(self.login)
        register_btn = QPushButton('注册新账号')
        register_btn.setProperty('secondary', True)
        register_btn.clicked.connect(self.open_register)
        form.addWidget(h); form.addSpacing(12); form.addWidget(QLabel('用户名')); form.addWidget(self.username); form.addWidget(QLabel('密码')); form.addWidget(self.password); form.addWidget(tip); form.addSpacing(12); form.addWidget(btn); form.addWidget(register_btn); form.addStretch()
        rightWrap = QFrame(); rw = QVBoxLayout(rightWrap); rw.setAlignment(Qt.AlignmentFlag.AlignCenter); rw.addWidget(card)
        root.addWidget(left, 3); root.addWidget(rightWrap, 2)
        self.main = None

    def open_register(self):
        dlg = RegisterDialog(self)
        if dlg.exec():
            self.username.setText(dlg.username.text().strip())
            self.password.clear()
            self.password.setFocus()

    def login(self):
        user = fetch_one('SELECT * FROM users WHERE username=? AND password=? AND enabled=1', (self.username.text().strip(), self.password.text().strip()))
        if not user:
            QMessageBox.warning(self, '登录失败', '用户名或密码不正确，或账号已被禁用。')
            return
        log_action(user['username'], '登录系统', f"角色：{user['role']}")
        self.main = MainWindow(user)
        self.main.show()
        self.close()
