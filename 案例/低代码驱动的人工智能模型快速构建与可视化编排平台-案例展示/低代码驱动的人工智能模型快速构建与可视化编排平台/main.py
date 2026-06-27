"""低代码驱动的人工智能模型快速构建与可视化编排平台 主入口"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.styles import load_stylesheet
from ui.login import LoginWindow
from ui.main_window import MainWindow
from core.auth import auth_engine

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(load_stylesheet())
    app.setApplicationName("低代码驱动的人工智能模型快速构建与可视化编排平台")
    login = LoginWindow()
    def on_login(user):
        main_win = MainWindow(user)
        main_win.show()
        login._main_win = main_win
    login.login_success.connect(on_login)
    login.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
