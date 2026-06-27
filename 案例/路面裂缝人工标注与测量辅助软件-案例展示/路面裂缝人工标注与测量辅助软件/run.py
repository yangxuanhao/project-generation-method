import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from app.core.storage import StorageManager
from app.core.image_factory import ensure_sample_images
from app.ui.login_dialog import LoginDialog
from app.ui.main_window import MainWindow


def main():
    ensure_sample_images(PROJECT_ROOT / 'assets' / 'samples')
    app = QApplication(sys.argv)
    qss_path = PROJECT_ROOT / 'assets' / 'styles' / 'light.qss'
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding='utf-8'))

    storage = StorageManager(PROJECT_ROOT / 'data')
    login = LoginDialog(storage)
    if login.exec() != LoginDialog.DialogCode.Accepted:
        return 0
    window = MainWindow(storage, login.current_user, PROJECT_ROOT)
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
