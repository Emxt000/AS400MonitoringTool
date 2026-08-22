import sys
import os
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui.styles import DARK_STYLESHEET
import ui.main_window

# 1. Force Windows Taskbar to pin/show the custom app icon instead of Python's generic icon
myappid = 'ibmi.dashboard.ecosystem.1'
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    
    # 2. Set global application level icon
    app_icon = QIcon(resource_path("logo.png"))
    app.setWindowIcon(app_icon)

    window = ui.main_window.IBMiDashboard()
    window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()