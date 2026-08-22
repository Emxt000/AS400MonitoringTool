# ui/styles.py

DARK_STYLESHEET = """
QMainWindow, QTabWidget::pane {
    background-color: #0d1117;
    border: none;
}
QTabBar::tab {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px 16px;
    border: 1px solid #30363d;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #0d1117;
    color: #58a6ff;
    border-color: #30363d;
    border-bottom: 2px solid #58a6ff;
}
QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: 'Segoe UI', 'SF Pro Display', -apple-system, sans-serif;
}
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 10px;
    font-weight: bold;
    font-size: 11px;
    color: #8b949e;
    padding-top: 6px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
}
QLineEdit, QComboBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
    font-size: 12px;
}
QComboBox QAbstractItemView {
    background-color: #161b22;
    color: #ffffff;
    selection-background-color: #1f6feb;
    border: 1px solid #30363d;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #58a6ff;
}
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}
QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border-color: #21262d;
}
QTableWidget {
    background-color: #161b22;
    gridline-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 8px;
    outline: none;
}
QTableWidget::item {
    border: none;
    padding: 4px;
}
QTableWidget::item:selected {
    background-color: transparent;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #0d1117;
    color: #8b949e;
    padding: 6px 10px;
    font-weight: 600;
    font-size: 12px;
    border: none;
    border-bottom: 2px solid #30363d;
}
"""