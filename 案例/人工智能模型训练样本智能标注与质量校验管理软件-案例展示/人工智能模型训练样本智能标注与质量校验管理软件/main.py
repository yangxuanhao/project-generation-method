import sys
from PyQt6.QtWidgets import QApplication
from app.core.database import init_db
from app.core.seed_data import seed_demo_data
from app.ui.login_window import LoginWindow
from app.resources import load_stylesheet


def main():
    init_db()
    seed_demo_data()
    app = QApplication(sys.argv)
    app.setApplicationName("人工智能模型训练样本智能标注与质量校验管理软件")
    app.setStyleSheet(load_stylesheet())
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
