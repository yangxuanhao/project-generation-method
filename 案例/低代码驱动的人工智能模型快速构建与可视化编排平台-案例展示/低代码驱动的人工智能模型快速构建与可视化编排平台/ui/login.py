"""登录/注册界面 - 低代码AI平台登录窗口"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QStackedWidget, QCheckBox, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen
from core.auth import auth_engine, Role, OpAction
import random

APP_TITLE = "低代码驱动的人工智能模型快速构建与可视化编排平台"

class GradientBackground(QWidget):
    """淡黄色渐变背景"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._particles = [(random.randint(0, 800), random.randint(0, 600), random.randint(1, 4)) for _ in range(40)]
        self._timer = QTimer(self); self._timer.timeout.connect(self._update_particles)
        self._timer.start(60)

    def _update_particles(self):
        for i, (x, y, s) in enumerate(self._particles):
            y = y - s if y > 0 else self.height()
            self._particles[i] = (x, y, s)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(255, 248, 225))
        for x, y, s in self._particles:
            alpha = 15 + int(y / max(1, self.height()) * 35)
            p.setBrush(QColor(255, 183, 0, alpha))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(x), int(y), s, s)

class LoginWindow(QWidget):
    login_success = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} - 登录")
        self.setFixedSize(860, 580)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self._drag_pos = None
        self._setup_ui()
        self._animation_entrance()

    def _setup_ui(self):
        self.bg = GradientBackground(self)
        self.bg.setGeometry(0, 0, 860, 580)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧信息面板
        left_panel = QFrame()
        left_panel.setFixedWidth(390)
        left_panel.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #FFF8E1,stop:1 #FFECB3); border-radius: 10px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(30, 28, 30, 28)

        close_layout = QHBoxLayout()
        btn_close = QPushButton("✕"); btn_close.setFixedSize(30, 30)
        btn_close.setStyleSheet("QPushButton{background:transparent;color:#795548;border:none;font-size:16px;} QPushButton:hover{color:#D84315;}")
        btn_close.clicked.connect(self.close)
        btn_min = QPushButton("─"); btn_min.setFixedSize(30, 30)
        btn_min.setStyleSheet("QPushButton{background:transparent;color:#795548;border:none;font-size:16px;} QPushButton:hover{color:#E65100;}")
        btn_min.clicked.connect(self.showMinimized)
        close_layout.addStretch(); close_layout.addWidget(btn_min); close_layout.addWidget(btn_close)
        left_layout.addLayout(close_layout)

        icon_label = QLabel("◈")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("color:#FF8F00;font-size:48px;margin:16px 0 6px;")
        left_layout.addWidget(icon_label)

        title = QLabel("低代码驱动的人工智能模型")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color:#4E342E;font-size:18px;font-weight:bold;")
        left_layout.addWidget(title)

        title2 = QLabel("快速构建与可视化编排平台")
        title2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title2.setStyleSheet("color:#4E342E;font-size:18px;font-weight:bold;margin-bottom:4px;")
        left_layout.addWidget(title2)

        subtitle = QLabel("AI模型 · 低代码 · 拖拽式编排")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color:#795548;font-size:13px;margin-bottom:8px;")
        left_layout.addWidget(subtitle)

        desc_lines = ["━━━━━━━━━━━━━━━━━━━━",
            "✦ 拖拽式AI流程画布编排", "✦ 内置低代码脚本编辑器",
            "✦ 6类AI模型模板一键创建", "✦ OpenCV视觉处理与3D渲染",
            "✦ 业务规则引擎冲突检测", "✦ 多角色RBAC权限调度",
            "✦ 数据事务管理与快照回溯"]
        for line in desc_lines:
            lbl = QLabel(line)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if line.startswith("✦"):
                lbl.setStyleSheet("color:#5D4037;font-size:11px;margin:2px 0;")
            elif line.startswith("━"):
                lbl.setStyleSheet("color:#FFD54F;font-size:11px;")
            left_layout.addWidget(lbl)
        left_layout.addStretch()

        bot_label = QLabel("默认账号: admin / admin123   developer / dev123")
        bot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bot_label.setStyleSheet("color:#FF8F00;font-size:10px;margin:6px 0;")
        left_layout.addWidget(bot_label)

        # 右侧登录/注册面板
        right_panel = QFrame()
        right_panel.setFixedWidth(400)
        right_panel.setStyleSheet("background:#FFF8E1;border-radius:10px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(36, 28, 36, 28)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._login_form())
        self.stack.addWidget(self._register_form())
        right_layout.addWidget(self.stack)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

    def _login_form(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w); layout.setSpacing(12)
        layout.addSpacing(20)
        t = QLabel("用户登录"); t.setStyleSheet("color:#4E342E;font-size:20px;font-weight:bold;")
        layout.addWidget(t); layout.addSpacing(8)

        self.txt_user = QLineEdit(); self.txt_user.setPlaceholderText("用户名"); self.txt_user.setText("admin")
        self.txt_user.setStyleSheet("font-size:13px;padding:9px 14px;")
        layout.addWidget(self.txt_user)

        self.txt_pwd = QLineEdit(); self.txt_pwd.setPlaceholderText("密码"); self.txt_pwd.setText("admin123")
        self.txt_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pwd.setStyleSheet("font-size:13px;padding:9px 14px;")
        layout.addWidget(self.txt_pwd)

        row = QHBoxLayout()
        self.chk_remember = QCheckBox("记住密码"); row.addWidget(self.chk_remember)
        row.addStretch()
        link_forgot = QPushButton("忘记密码?"); link_forgot.setFlat(True)
        link_forgot.setStyleSheet("color:#FF8F00;border:none;font-size:11px;text-decoration:underline;min-width:0;background:transparent;")
        row.addWidget(link_forgot)
        layout.addLayout(row)

        btn_login = QPushButton("登  录")
        btn_login.setObjectName("primary"); btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.clicked.connect(self._do_login)
        layout.addWidget(btn_login)

        layout.addSpacing(6)
        link_reg = QPushButton("还没有账号？立即注册 →"); link_reg.setFlat(True)
        link_reg.setStyleSheet("color:#795548;border:none;font-size:11px;min-width:0;background:transparent;")
        link_reg.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        layout.addWidget(link_reg)
        layout.addStretch()
        return w

    def _register_form(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w); layout.setSpacing(10)
        layout.addSpacing(12)
        t = QLabel("账号注册"); t.setStyleSheet("color:#4E342E;font-size:20px;font-weight:bold;")
        layout.addWidget(t); layout.addSpacing(2)

        self.reg_user = QLineEdit(); self.reg_user.setPlaceholderText("用户名（2位以上）")
        layout.addWidget(self.reg_user)
        self.reg_pwd = QLineEdit(); self.reg_pwd.setPlaceholderText("密码（4位以上）")
        self.reg_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.reg_pwd)
        self.reg_pwd2 = QLineEdit(); self.reg_pwd2.setPlaceholderText("确认密码")
        self.reg_pwd2.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.reg_pwd2)

        self.reg_role = QComboBox()
        for role in Role: self.reg_role.addItem(role.value, role)
        self.reg_role.setCurrentText(Role.GUEST.value)
        layout.addWidget(self.reg_role)

        btn_reg = QPushButton("注  册"); btn_reg.setObjectName("primary")
        btn_reg.clicked.connect(self._do_register)
        layout.addWidget(btn_reg)

        link_back = QPushButton("← 返回登录"); link_back.setFlat(True)
        link_back.setStyleSheet("color:#795548;border:none;font-size:11px;min-width:0;background:transparent;")
        link_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(link_back)
        layout.addStretch()
        return w

    def _do_login(self):
        username = self.txt_user.text().strip()
        password = self.txt_pwd.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码"); return
        user = auth_engine.authenticate(username, password)
        if user:
            self.hide(); self.login_success.emit(user)
        else:
            QMessageBox.critical(self, "登录失败", "用户名或密码错误，或账号已被锁定")

    def _do_register(self):
        username = self.reg_user.text().strip()
        pwd = self.reg_pwd.text().strip()
        pwd2 = self.reg_pwd2.text().strip()
        if len(username) < 2 or len(pwd) < 4:
            QMessageBox.warning(self, "提示", "用户名至少2位，密码至少4位"); return
        if pwd != pwd2:
            QMessageBox.warning(self, "提示", "两次密码不一致"); return
        user = auth_engine.register(username, pwd, self.reg_role.currentData())
        if user:
            QMessageBox.information(self, "成功", f"注册成功！角色：{user.role.value}\n请返回登录。")
            self.stack.setCurrentIndex(0)
        else:
            QMessageBox.critical(self, "失败", "用户名已存在")

    def _animation_entrance(self):
        self.setWindowOpacity(0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(400); self.anim.setStartValue(0)
        self.anim.setEndValue(1); self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() < 40:
            self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
