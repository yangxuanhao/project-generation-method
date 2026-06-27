"""主窗口 - 13模块菜单 + 状态栏 + 热更新支持"""
from PyQt6.QtWidgets import (QMainWindow, QMenuBar, QMenu, QStatusBar, QTabWidget,
    QToolBar, QDockWidget, QListWidget, QLabel, QMessageBox, QWidget, QVBoxLayout, QApplication)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFont
from core.auth import Role, OpAction, auth_engine
from ui.styles import load_stylesheet
import importlib, sys, os

APP_TITLE = "低代码驱动的人工智能模型快速构建与可视化编排平台"

class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._modules = {}
        self._module_widgets = {}
        self.setWindowTitle(f"{APP_TITLE} | 用户: {user.username} | 角色: {user.role.value}")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 820)
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._setup_central()
        self._setup_quick_nav()
        self._hot_reload_timer = QTimer(self)
        self._hot_reload_timer.timeout.connect(self._check_hot_reload)
        self._hot_reload_timer.start(3000)
        self._file_mtimes = {}
        self.statusBar().showMessage(f"✅ 欢迎 {user.username} | 系统就绪 | 13个业务模块已加载", 5000)

    def _setup_menu(self):
        mb = self.menuBar()
        sys_menu = mb.addMenu("⚙ 系统")
        sys_menu.addAction("🔄 刷新模块", self._refresh_modules)
        sys_menu.addAction("🔑 切换账号", self._switch_account)
        sys_menu.addSeparator()
        sys_menu.addAction("🚪 退出系统", self.close)

        menus = [
            ("📊 工作台", "dashboard", "项目总览与快速导航"),
            ("🎨 模型设计器", "model_designer", "可视化画布编排AI流程"),
            ("💻 低代码编辑器", "lowcode_editor", "Python脚本低代码编写"),
            ("🚀 模型训练", "model_training", "AI模型训练启停控制"),
            ("👁 视觉实验室(OpenCV)", "vision_lab", "图像预处理与视觉推理"),
            ("🌐 3D可视化", "vision_3d", "3D点云与模型结构渲染"),
            ("📐 规则配置器", "rule_config", "业务规则可视化配置"),
            ("💾 数据管理", "data_manager", "多源数据接入与事务管理"),
            ("📋 任务管控", "task_manager", "任务队列与运行日志"),
            ("📁 项目管理", "project_manager", "项目资源分类管理"),
            ("🧩 组件市场", "component_market", "节点/脚本/规则组件"),
            ("📈 报表中心", "report_center", "模型指标与训练报表"),
            ("🛡 系统管理", "system_admin", "用户/权限/日志管理"),
        ]
        for name, mod_key, desc in menus:
            menu = mb.addMenu(name)
            menu.addAction(f"📌 打开{name[2:]}", lambda k=mod_key: self._open_module(k))
            menu.addAction(f"📖 {desc}", lambda k=mod_key: self._open_module(k))
            menu.addSeparator()
            menu.addAction("🔄 刷新", lambda k=mod_key: self._reload_module(k))

        help_menu = mb.addMenu("❓ 帮助")
        help_menu.addAction("📖 使用手册", lambda: QMessageBox.information(self, "帮助",
            f"{APP_TITLE}\n\n1. 从工作台新建项目或选择模板\n2. 在模型设计器中拖拽节点编排流程\n3. 使用低代码编辑器编写节点逻辑\n4. 配置业务规则后启动训练\n5. 在视觉实验室查看处理结果\n6. 报表中心查看训练指标"))
        help_menu.addAction("ℹ 关于系统", lambda: QMessageBox.about(self, "关于",
            f"{APP_TITLE}\n\n核心技术栈: Python3 + PyQt6 + OpenCV + OpenGL\n核心引擎: RBAC权限调度 | 状态流转 | 规则引擎 | 数据一致性"))

    def _setup_toolbar(self):
        tb = QToolBar("快捷工具栏"); tb.setMovable(False); self.addToolBar(tb)
        actions = [
            ("📊工作台", "dashboard"), ("🎨设计器", "model_designer"), ("💻编辑器", "lowcode_editor"),
            ("🚀训练", "model_training"), ("👁视觉", "vision_lab"), ("🌐3D", "vision_3d"),
            ("📐规则", "rule_config"), ("💾数据", "data_manager"), ("📋任务", "task_manager"),
            ("📁项目", "project_manager"), ("🧩市场", "component_market"), ("📈报表", "report_center"),
        ]
        for label, mod_key in actions:
            act = QAction(label, self)
            act.triggered.connect(lambda checked, k=mod_key: self._open_module(k))
            tb.addAction(act)

    def _setup_statusbar(self):
        self._perm_label = QLabel(f"🔒 角色: {self.user.role.value}")
        self._perm_label.setStyleSheet("color:#E65100;padding:2px 8px;")
        self.statusBar().addPermanentWidget(self._perm_label)

    def _setup_central(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.setDocumentMode(True)
        self.setCentralWidget(self.tab_widget)
        self._open_module("dashboard")

    def _setup_quick_nav(self):
        dock = QDockWidget("📂 模块导航", self)
        nav_list = QListWidget()
        modules_list = ["工作台", "模型设计器", "低代码编辑器", "模型训练",
                        "视觉实验室", "3D可视化", "规则配置器", "数据管理",
                        "任务管控", "项目管理", "组件市场", "报表中心", "系统管理"]
        nav_list.addItems(modules_list)
        nav_list.itemClicked.connect(lambda item: self._open_module_by_name(item.text()))
        nav_list.setMaximumWidth(160)
        dock.setWidget(nav_list)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    def _open_module(self, mod_key: str):
        if not auth_engine.check_permission(self.user, mod_key, OpAction.VIEW):
            QMessageBox.warning(self, "权限不足", f"您没有访问 [{mod_key}] 模块的权限")
            return
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i).startswith(self._mod_name(mod_key)):
                self.tab_widget.setCurrentIndex(i); return
        widget = self._load_module_widget(mod_key)
        if widget:
            idx = self.tab_widget.addTab(widget, f"{self._mod_icon(mod_key)} {self._mod_name(mod_key)}")
            self.tab_widget.setCurrentIndex(idx)

    def _open_module_by_name(self, name: str):
        name_map = {"工作台":"dashboard","模型设计器":"model_designer","低代码编辑器":"lowcode_editor",
            "模型训练":"model_training","视觉实验室":"vision_lab","3D可视化":"vision_3d",
            "规则配置器":"rule_config","数据管理":"data_manager","任务管控":"task_manager",
            "项目管理":"project_manager","组件市场":"component_market","报表中心":"report_center",
            "系统管理":"system_admin"}
        key = name_map.get(name)
        if key: self._open_module(key)

    def _load_module_widget(self, mod_key: str):
        if mod_key in self._module_widgets:
            return self._module_widgets[mod_key]
        try:
            module = importlib.import_module(f"modules.{mod_key}")
            if hasattr(module, 'get_module_widget'):
                widget = module.get_module_widget(self.user)
                self._module_widgets[mod_key] = widget
                self._modules[mod_key] = module
                self._track_file(mod_key, module)
                from PyQt6.QtWidgets import QScrollArea
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setWidget(widget)
                scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
                return scroll
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "模块加载失败", f"模块 [{mod_key}] 加载异常:\n{str(e)[:200]}")
            return QLabel(f"模块加载失败: {e}")

    def _reload_module(self, mod_key: str):
        if mod_key in self._modules:
            importlib.reload(self._modules[mod_key])
            if mod_key in self._module_widgets:
                del self._module_widgets[mod_key]
            self._open_module(mod_key)
        self.statusBar().showMessage(f"🔄 模块 [{mod_key}] 已热更新", 3000)

    def _refresh_modules(self):
        for mod_key in list(self._modules.keys()):
            self._reload_module(mod_key)

    def _check_hot_reload(self):
        for mod_key, module in list(self._modules.items()):
            try:
                mod_file = module.__file__
                if mod_file and os.path.exists(mod_file):
                    mtime = os.path.getmtime(mod_file)
                    if mod_key in self._file_mtimes and self._file_mtimes[mod_key] != mtime:
                        self.statusBar().showMessage(f"⚡ 检测到模块 [{mod_key}] 变更，自动热更新...", 2000)
                        self._reload_module(mod_key)
                    self._file_mtimes[mod_key] = mtime
            except: pass

    def _track_file(self, mod_key: str, module):
        try:
            mod_file = module.__file__
            if mod_file and os.path.exists(mod_file):
                self._file_mtimes[mod_key] = os.path.getmtime(mod_file)
        except: pass

    def _close_tab(self, index: int):
        self.tab_widget.removeTab(index)

    def _switch_account(self):
        self.hide()
        from ui.login import LoginWindow
        self.login_win = LoginWindow()
        self.login_win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.login_win.login_success.connect(self._on_relogin)
        self.login_win.destroyed.connect(self._on_login_closed)
        self.login_win.show()

    def _on_login_closed(self):
        if not self.isVisible():
            self.show()
            self.statusBar().showMessage("已取消账号切换", 3000)

    def _on_relogin(self, user):
        self.user = user
        self.setWindowTitle(f"{APP_TITLE} | 用户: {user.username} | 角色: {user.role.value}")
        self._perm_label.setText(f"🔒 角色: {user.role.value}")
        self.tab_widget.clear(); self._module_widgets.clear(); self._modules.clear()
        self._open_module("dashboard"); self.show()
        self.statusBar().showMessage(f"✅ 已切换至 {user.username} ({user.role.value})", 5000)

    def _mod_name(self, key: str) -> str:
        names = {"dashboard":"工作台","model_designer":"模型设计器","lowcode_editor":"低代码编辑器",
            "model_training":"模型训练","vision_lab":"视觉实验室","vision_3d":"3D可视化",
            "rule_config":"规则配置器","data_manager":"数据管理","task_manager":"任务管控",
            "project_manager":"项目管理","component_market":"组件市场","report_center":"报表中心",
            "system_admin":"系统管理"}
        return names.get(key, key)

    def _mod_icon(self, key: str) -> str:
        icons = {"dashboard":"📊","model_designer":"🎨","lowcode_editor":"💻","model_training":"🚀",
            "vision_lab":"👁","vision_3d":"🌐","rule_config":"📐","data_manager":"💾",
            "task_manager":"📋","project_manager":"📁","component_market":"🧩","report_center":"📈",
            "system_admin":"🛡"}
        return icons.get(key, "📦")
