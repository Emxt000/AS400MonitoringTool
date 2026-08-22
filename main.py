# main.py

import sys
from PyQt6.QtWidgets import QApplication
from ui.styles import DARK_STYLESHEET

import ui.main_window


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    window = ui.main_window.IBMiDashboard()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()