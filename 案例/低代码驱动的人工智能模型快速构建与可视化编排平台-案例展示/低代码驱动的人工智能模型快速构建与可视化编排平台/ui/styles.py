"""低代码AI平台统一样式表 - 淡黄色专业主题"""
import os

APP_THEME = """
/* 全局淡黄色主题 */
QMainWindow, QDialog { background-color: #FFF8E1; color: #4E342E; }
QWidget { font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 12px; }

/* 菜单栏 */
QMenuBar { background: #FFECB3; color: #4E342E; border-bottom: 2px solid #FFD54F; padding: 2px; }
QMenuBar::item:selected { background: #FFE082; color: #E65100; border-radius: 4px; }
QMenu { background: #FFFDE7; color: #4E342E; border: 1px solid #FFD54F; padding: 4px; border-radius: 6px; }
QMenu::item { padding: 6px 28px; border-radius: 4px; }
QMenu::item:selected { background: #FFECB3; color: #E65100; }
QMenu::separator { height: 1px; background: #FFD54F; margin: 3px 10px; }

/* 工具栏 */
QToolBar { background: #FFECB3; border-bottom: 1px solid #FFD54F; padding: 2px; spacing: 4px; }
QToolButton { background: transparent; color: #5D4037; border: 1px solid transparent; border-radius: 4px; padding: 4px 10px; }
QToolButton:hover { background: #FFE082; color: #E65100; border-color: #FFB300; }
QToolButton:checked { background: #FFE082; color: #E65100; border-color: #FFB300; }

/* 标签页 */
QTabWidget::pane { border: 1px solid #FFD54F; background: #FFF8E1; border-radius: 6px; }
QTabBar::tab { background: #FFFDE7; color: #5D4037; border: 1px solid #FFD54F; padding: 6px 16px;
    margin-right: 2px; border-radius: 6px 6px 0 0; }
QTabBar::tab:selected { background: #FFECB3; color: #E65100; border-bottom: 2px solid #FF8F00; }
QTabBar::tab:hover { background: #FFE082; color: #E65100; }

/* 按钮 */
QPushButton { background: #FFECB3; color: #5D4037; border: 1px solid #FFD54F; border-radius: 6px;
    padding: 6px 16px; font-weight: bold; min-width: 70px; }
QPushButton:hover { background: #FFE082; border-color: #FF8F00; color: #E65100; }
QPushButton:pressed { background: #FFD54F; }
QPushButton:disabled { background: #F5F5DC; color: #BCAAA4; border-color: #D7CCC8; }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FF8F00,stop:1 #FFB300);
    color: white; border: none; font-size: 13px; padding: 8px 24px; }
QPushButton#danger { background: #FFCCBC; color: #D84315; border-color: #FF8A65; }
QPushButton#danger:hover { background: #FFAB91; }
QPushButton#success { background: #C8E6C9; color: #2E7D32; border-color: #81C784; }
QPushButton#success:hover { background: #A5D6A7; }
QPushButton#warning { background: #FFECB3; color: #F57F17; border-color: #FFB300; }
QPushButton#warning:hover { background: #FFE082; }

/* 输入框 */
QLineEdit, QTextEdit, QPlainTextEdit { background: #FFFFFF; color: #4E342E; border: 1px solid #FFD54F;
    border-radius: 6px; padding: 6px; selection-background-color: #FFE082; }
QLineEdit:focus, QTextEdit:focus { border-color: #FF8F00; }
QSpinBox, QDoubleSpinBox { background: #FFFFFF; color: #E65100; border: 1px solid #FFD54F;
    border-radius: 6px; padding: 4px; font-weight: bold; }

/* 表格 */
QTableWidget, QTableView { background: #FFFDE7; color: #4E342E; border: 1px solid #FFD54F;
    gridline-color: #FFECB3; border-radius: 6px; selection-background-color: #FFE082; }
QHeaderView::section { background: #FFECB3; color: #E65100; border: 1px solid #FFD54F;
    padding: 6px; font-weight: bold; }
QTableWidget::item:hover { background: #FFF8E1; }

/* 列表 */
QListWidget, QListView { background: #FFFDE7; color: #4E342E; border: 1px solid #FFD54F;
    border-radius: 6px; selection-background-color: #FFE082; outline: none; }
QListWidget::item { padding: 4px 10px; border-radius: 3px; }
QListWidget::item:selected { background: #FFE082; color: #E65100; }
QListWidget::item:hover { background: #FFF8E1; }

/* 树形控件 */
QTreeWidget, QTreeView { background: #FFFDE7; color: #4E342E; border: 1px solid #FFD54F;
    border-radius: 6px; selection-background-color: #FFE082; }
QTreeWidget::item { padding: 3px; }
QTreeWidget::item:selected { background: #FFE082; color: #E65100; }

/* 滚动条 */
QScrollBar:vertical { background: #FFF8E1; width: 12px; border-radius: 6px; }
QScrollBar::handle:vertical { background: #FFD54F; border-radius: 6px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #FF8F00; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #FFF8E1; height: 12px; border-radius: 6px; }
QScrollBar::handle:horizontal { background: #FFD54F; border-radius: 6px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: #FF8F00; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* 分组框 */
QGroupBox { color: #E65100; border: 1px solid #FFD54F; border-radius: 8px; margin-top: 14px;
    padding-top: 14px; font-weight: bold; font-size: 13px; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; background: #FFF8E1; }

/* 滑块 */
QSlider::groove:horizontal { background: #FFECB3; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal { background: #FF8F00; width: 16px; height: 16px; margin: -5px 0;
    border-radius: 8px; }
QSlider::sub-page:horizontal { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FFB300,stop:1 #FF8F00);
    border-radius: 3px; }

/* 进度条 */
QProgressBar { background: #FFFFFF; border: 1px solid #FFD54F; border-radius: 6px; text-align: center;
    color: #4E342E; font-weight: bold; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FF8F00,stop:1 #FFB300);
    border-radius: 5px; }

/* 复选框/单选框 */
QCheckBox, QRadioButton { color: #4E342E; spacing: 6px; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; border: 2px solid #FFD54F;
    border-radius: 3px; background: #FFFFFF; }
QCheckBox::indicator:checked { background: #FF8F00; border-color: #FF8F00; }
QRadioButton::indicator:checked { background: #FF8F00; border-color: #FF8F00; }

/* 下拉框 */
QComboBox { background: #FFFFFF; color: #4E342E; border: 1px solid #FFD54F; border-radius: 6px;
    padding: 4px 10px; min-width: 100px; }
QComboBox:hover { border-color: #FF8F00; }
QComboBox QAbstractItemView { background: #FFFDE7; color: #4E342E; border: 1px solid #FFD54F;
    selection-background-color: #FFE082; }
QComboBox::drop-down { border: none; padding-right: 6px; }

/* 停靠窗口 */
QDockWidget { color: #E65100; titlebar-close-icon: none; }
QDockWidget::title { background: #FFECB3; border-bottom: 2px solid #FFD54F; padding: 6px; }

/* 状态栏 */
QStatusBar { background: #FFECB3; color: #5D4037; border-top: 1px solid #FFD54F; }

/* 滚动区域 */
QScrollArea { border: none; background: transparent; }

/* 分割线 */
QSplitter::handle { background: #FFD54F; width: 2px; }
QSplitter::handle:hover { background: #FF8F00; }

/* 链接标签 */
QLabel#link { color: #E65100; text-decoration: underline; }
QLabel#title { color: #E65100; font-size: 18px; font-weight: bold; }
QLabel#subtitle { color: #795548; font-size: 11px; }
QLabel#badge { background: #FFE082; color: #E65100; border-radius: 10px; padding: 2px 8px; font-size: 10px; }
"""

def get_icons_dir():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources")

def load_stylesheet() -> str:
    return APP_THEME
