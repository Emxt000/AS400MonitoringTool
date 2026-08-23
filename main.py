import sys
import os
import ctypes
import subprocess

# Prevent CMD window flashing without breaking C-extensions
if sys.platform == "win32":
    # 1. Detach console if running in a compiled binary
    if getattr(sys, 'frozen', False):
        try:
            ctypes.windll.kernel32.FreeConsole()
        except Exception:
            pass

        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    # 2. Safely apply CREATE_NO_WINDOW (0x08000000) to subprocess.Popen
    _orig_init = subprocess.Popen.__init__

    def _safe_popen_init(self, *args, **kwargs):
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        _orig_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = _safe_popen_init

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui.styles import DARK_STYLESHEET
import ui.main_window

# Force Windows Taskbar to pin/show custom app icon
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
    
    app_icon = QIcon(resource_path("logo.png"))
    app.setWindowIcon(app_icon)

    window = ui.main_window.IBMiDashboard()
    window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()