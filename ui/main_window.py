import platform
import subprocess
import sys
import os

# Add project root directory to sys.path so 'worker' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QCursor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
    QHBoxLayout, QGroupBox, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QScrollArea, QFrame, QGridLayout, QProgressBar,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QApplication
)

from worker import WorkerThread
from ui.log_viewer import LogViewerWidget
from ui.widgets import RefreshStatusWidget, StatusBadgesWidget, SubsystemGridWidget


def is_vpn_connected(target_ip="189.88.18.66"):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    command = ["ping", param, "1", "-w", "1000", target_ip]
    try:
        output = subprocess.run(command, capture_output=True, text=True)
        return output.returncode == 0
    except Exception:
        return False


class SubsystemDetailDialog(QDialog):
    """Modal popup displaying QSYS2.SUBSYSTEM_INFO detailed metrics with inactive highlights."""
    def __init__(self, server_name, subsystem_data=None, timestamp_str="", parent=None):
        super().__init__(parent)
        self.server_name = server_name
        self.subsystem_data = subsystem_data or []
        self.setWindowTitle(f"{server_name} - Detailed Subsystem Status")
        self.resize(850, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
                border: 2px solid #2ea043;
                border-radius: 12px;
            }
            QLabel { color: #c9d1d9; background-color: transparent; }
            QTableWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                gridline-color: #21262d;
                color: #c9d1d9;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #21262d;
                color: #8b949e;
                font-weight: bold;
                border: none;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Title
        title_str = f"{server_name} Detailed Subsystem Status"
        if timestamp_str:
            title_str += f" ({timestamp_str})"
        title_lbl = QLabel(title_str)
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #ffffff; background-color: transparent;")
        layout.addWidget(title_lbl)

        # 5-Column Table View
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Subsystem Description ▲", "Status", "Current Active Jobs", "Library", "Text Description"
        ])
        
        # Make cells read-only
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 110)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.populate_subsystem_details()
        layout.addWidget(self.table)

    def show_centered(self):
        """Always centers the modal directly relative to the main window or active screen."""
        if self.parent():
            top_level = self.parent().window()
            parent_geo = top_level.geometry()
            
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)
        else:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geo = screen.availableGeometry()
                x = screen_geo.x() + (screen_geo.width() - self.width()) // 2
                y = screen_geo.y() + (screen_geo.height() - self.height()) // 2
                self.move(x, y)
                
        self.exec()

    def populate_subsystem_details(self):
        from config import EXPECTED_SUBSYSTEMS
        
        expected_list = EXPECTED_SUBSYSTEMS.get(self.server_name, [])
        active_dict = {}

        # Map active subsystems
        for sub in self.subsystem_data:
            if isinstance(sub, dict):
                s_name = sub.get("name", "").upper()
                active_dict[s_name] = sub
            elif isinstance(sub, str):
                s_name = sub.upper()
                active_dict[s_name] = {"name": s_name, "status": "ACTIVE", "active_jobs": 0, "library": "QSYS", "description": ""}

        all_display_rows = []
        
        # 1. Process expected list to identify running vs missing
        for exp_name in expected_list:
            exp_upper = exp_name.upper()
            if exp_upper in active_dict:
                all_display_rows.append(active_dict[exp_upper])
            else:
                # Flag missing subsystem as INACTIVE
                all_display_rows.append({
                    "name": exp_upper,
                    "status": "INACTIVE",
                    "active_jobs": 0,
                    "library": "QSYS",
                    "description": "Subsystem Stopped / Down"
                })

        # 2. Add extra active subsystems not explicitly in config
        for s_name, data in active_dict.items():
            if s_name not in [e.upper() for e in expected_list]:
                all_display_rows.append(data)

        self.table.setRowCount(len(all_display_rows))
        
        for row, sub in enumerate(all_display_rows):
            name = sub.get("name", "")
            status = str(sub.get("status", "ACTIVE")).upper()
            active_jobs = str(sub.get("active_jobs", 0))
            library = sub.get("library", "")
            desc = sub.get("description", "")

            is_inactive = status in ["INACTIVE", "DOWN", "INACTIVE/OFF"]

            items = [
                QTableWidgetItem(name),
                QTableWidgetItem(status),
                QTableWidgetItem(active_jobs),
                QTableWidgetItem(library),
                QTableWidgetItem(desc)
            ]

            items[1].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            items[2].setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Apply flags to disable editing per item and apply styling
            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if is_inactive:
                    item.setForeground(QColor("#f85149"))
                    item.setBackground(QColor("#361718"))
                    item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.table.setItem(row, col, item)


class LinearGauge(QWidget):
    """Slim linear progress bar for CPU/ASP metrics."""
    def __init__(self, title, initial_value=0.0, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #8b949e; background-color: transparent;")

        self.val_label = QLabel("0.0%")
        self.val_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.val_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        top_h = QHBoxLayout()
        top_h.addWidget(self.title_label)
        top_h.addStretch()
        top_h.addWidget(self.val_label)
        layout.addLayout(top_h)

        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(8)
        self.pbar.setTextVisible(False)
        layout.addWidget(self.pbar)

        self.set_value(initial_value)

    def set_value(self, val):
        val_float = float(val)
        self.val_label.setText(f"{val_float:.1f}%")
        self.pbar.setValue(min(100, int(val_float)))

        if val_float >= 90.0:
            bar_color = "#f85149"
            self.val_label.setStyleSheet("color: #f85149; background-color: transparent;")
        elif val_float >= 80.0:
            bar_color = "#e3b341"
            self.val_label.setStyleSheet("color: #e3b341; background-color: transparent;")
        else:
            bar_color = "#388bfd"
            self.val_label.setStyleSheet("color: #ffffff; background-color: transparent;")

        self.pbar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #21262d;
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 4px;
            }}
        """)


class LparCardWidget(QFrame):
    """Grid card representing a single LPAR system status."""
    def __init__(self, server_name, parent=None):
        super().__init__(parent)
        self.server_name = server_name
        self.current_subsystems_data = []
        
        self.setMinimumWidth(340)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(6)

        # Card Header
        header_layout = QHBoxLayout()
        self.name_label = QLabel(server_name)
        self.name_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #ffffff; background-color: transparent;")

        self.status_badge = QLabel("OFFLINE ●")
        self.status_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.status_badge.setStyleSheet("color: #8b949e; background-color: transparent;")

        header_layout.addWidget(self.name_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_badge)
        self.main_layout.addLayout(header_layout)

        # CPU & ASP Gauges
        gauges_layout = QHBoxLayout()
        gauges_layout.setSpacing(12)
        self.cpu_gauge = LinearGauge("CPU")
        self.asp_gauge = LinearGauge("ASP")
        gauges_layout.addWidget(self.cpu_gauge, stretch=1)
        gauges_layout.addWidget(self.asp_gauge, stretch=1)
        self.main_layout.addLayout(gauges_layout)

        # Active Jobs Counter
        jobs_layout = QHBoxLayout()
        jobs_lbl = QLabel("Active Jobs")
        jobs_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        jobs_lbl.setStyleSheet("color: #8b949e; background-color: transparent;")
        self.jobs_val_label = QLabel("0")
        self.jobs_val_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.jobs_val_label.setStyleSheet("color: #ffffff; background-color: transparent;")
        
        jobs_layout.addWidget(jobs_lbl)
        jobs_layout.addStretch()
        jobs_layout.addWidget(self.jobs_val_label)
        self.main_layout.addLayout(jobs_layout)

        # Subsystems Header Label
        sub_header = QHBoxLayout()
        sub_lbl = QLabel("Subsystems")
        sub_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        sub_lbl.setStyleSheet("color: #8b949e; background-color: transparent;")
        sub_header.addWidget(sub_lbl)
        sub_header.addStretch()
        self.main_layout.addLayout(sub_header)

        # Subsystem Container Frame
        self.subsystem_container = QWidget()
        self.subsys_layout = QVBoxLayout(self.subsystem_container)
        self.subsys_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.subsystem_container)

        # Network Services Label & Container
        net_lbl = QLabel("Network Services")
        net_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        net_lbl.setStyleSheet("color: #8b949e; margin-top: 2px; background-color: transparent;")
        self.main_layout.addWidget(net_lbl)

        self.ports_container = QWidget()
        self.ports_layout = QVBoxLayout(self.ports_container)
        self.ports_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.ports_container)

        self.set_card_style(is_critical=False)

    def open_subsystem_modal(self, server_name):
        dialog = SubsystemDetailDialog(
            server_name=self.server_name, 
            subsystem_data=self.current_subsystems_data, 
            parent=self
        )
        dialog.show_centered()

    def set_card_style(self, is_critical=False):
        if is_critical:
            self.setStyleSheet("""
                LparCardWidget {
                    background-color: #161b22;
                    border: 2px solid #f85149;
                    border-radius: 10px;
                }
                QLabel {
                    background-color: transparent;
                }
            """)
        else:
            self.setStyleSheet("""
                LparCardWidget {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 10px;
                }
                QLabel {
                    background-color: transparent;
                }
            """)

    def update_data(self, data):
        status = data.get("status", "OFFLINE")
        cpu = float(data.get("cpu", 0.0))
        asp = float(data.get("asp", 0.0))
        jobs = data.get("jobs", 0)

        self.current_subsystems_data = data.get("subsystems", [])

        # Critical threshold strictly ASP >= 90%
        is_critical = asp >= 90.0 or status == "AUTH_ERROR"
        self.set_card_style(is_critical=is_critical)

        if status == "ONLINE":
            if is_critical:
                self.status_badge.setText("CRITICAL ●")
                self.status_badge.setStyleSheet("color: #f85149; font-weight: bold; background-color: transparent;")
            else:
                self.status_badge.setText("ONLINE ●")
                self.status_badge.setStyleSheet("color: #3fb950; font-weight: bold; background-color: transparent;")
        else:
            self.status_badge.setText(f"{status} ●")
            self.status_badge.setStyleSheet("color: #8b949e; font-weight: bold; background-color: transparent;")

        self.cpu_gauge.set_value(cpu)
        self.asp_gauge.set_value(asp)
        self.jobs_val_label.setText(f"{jobs:,}")

        # Render Subsystems
        for i in reversed(range(self.subsys_layout.count())):
            w = self.subsys_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        sub_widget = SubsystemGridWidget(
            server_name=self.server_name,
            active_subsystems=self.current_subsystems_data,
            on_expand_callback=self.open_subsystem_modal,
            parent=self
        )
        self.subsys_layout.addWidget(sub_widget)

        # Render Ports
        for i in reversed(range(self.ports_layout.count())):
            w = self.ports_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        ports = data.get("ports", [])
        if ports:
            badges_widget = StatusBadgesWidget(ports)
            self.ports_layout.addWidget(badges_widget)


class GlobalAlertsWidget(QGroupBox):
    """Top bar displaying overall ecosystem status metrics."""
    def __init__(self, parent=None):
        super().__init__("Global Alerts and Status", parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(24)

        # Total Down Services
        self.down_count_lbl = QLabel("0")
        self.down_count_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.down_count_lbl.setStyleSheet("color: #f85149; background-color: transparent;")
        
        down_desc = QLabel("Total Down\nServices")
        down_desc.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        down_desc.setStyleSheet("color: #f85149; background-color: transparent;")

        m1_layout = QHBoxLayout()
        m1_layout.addWidget(self.down_count_lbl)
        m1_layout.addWidget(down_desc)
        layout.addLayout(m1_layout)

        # Overloaded LPARs
        self.overload_lbl = QLabel("0 Server Overloaded")
        self.overload_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.overload_lbl.setStyleSheet("color: #e3b341; background-color: transparent;")

        m2_layout = QHBoxLayout()
        icon2 = QLabel("⚠️")
        icon2.setFont(QFont("Segoe UI", 12))
        icon2.setStyleSheet("background-color: transparent;")
        m2_layout.addWidget(icon2)
        m2_layout.addWidget(self.overload_lbl)
        layout.addLayout(m2_layout)

        # Subsystem Overall Status
        self.sub_status_lbl = QLabel("All Subsystems Active")
        self.sub_status_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.sub_status_lbl.setStyleSheet("color: #3fb950; background-color: transparent;")

        m3_layout = QHBoxLayout()
        icon3 = QLabel("✅")
        icon3.setFont(QFont("Segoe UI", 12))
        icon3.setStyleSheet("background-color: transparent;")
        m3_layout.addWidget(icon3)
        m3_layout.addWidget(self.sub_status_lbl)
        layout.addLayout(m3_layout)

    def update_summary(self, data_list):
        total_down_services = 0
        overloaded_servers = []
        total_online = 0

        for sys_info in data_list:
            if sys_info.get("status") == "ONLINE":
                total_online += 1
                ports = sys_info.get("ports", [])
                down_ports = [p for p in ports if not p.get("is_up")]
                total_down_services += len(down_ports)

                if float(sys_info.get("asp", 0.0)) >= 90.0:
                    overloaded_servers.append(sys_info.get("server", ""))

        self.down_count_lbl.setText(str(total_down_services))

        if overloaded_servers:
            srv_str = ", ".join(overloaded_servers)
            self.overload_lbl.setText(f"{len(overloaded_servers)} Server Overloaded\n({srv_str})")
            self.overload_lbl.setStyleSheet("color: #f85149; font-weight: bold; background-color: transparent;")
        else:
            self.overload_lbl.setText("0 Server Overloaded")
            self.overload_lbl.setStyleSheet("color: #e3b341; font-weight: bold; background-color: transparent;")

        self.sub_status_lbl.setText(f"All Subsystems Active ({total_online}/{len(data_list)})")

"""For Logo/Icon"""
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class IBMiDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IBM i Native Ecosystem Dashboard")
        self.setWindowIcon(QIcon(resource_path("logo.png")))
        self.resize(1750, 950)

        self.is_monitoring = False
        self.card_widgets = {}

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.live_monitor_widget = QWidget()
        self.init_live_monitor_ui()
        self.tabs.addTab(self.live_monitor_widget, "📊 Live Monitor")

        self.log_viewer_widget = LogViewerWidget()
        self.tabs.addTab(self.log_viewer_widget, "📜 Log Viewer History")

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fetch_data)

    def init_live_monitor_ui(self):
        main_layout = QVBoxLayout(self.live_monitor_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        top_bar_layout = QHBoxLayout()
        top_bar_layout.setSpacing(12)

        cred_group = QGroupBox("IBM i Access Credentials")
        cred_layout = QHBoxLayout(cred_group)
        cred_layout.setContentsMargins(12, 10, 12, 10)
        cred_layout.setSpacing(10)

        lbl_user = QLabel("Username:")
        lbl_user.setStyleSheet("background-color: transparent;")
        cred_layout.addWidget(lbl_user)

        self.user_input = QLineEdit("")
        self.user_input.setPlaceholderText("Enter Username")
        self.user_input.setFixedWidth(120)
        cred_layout.addWidget(self.user_input)

        lbl_pass = QLabel("Password:")
        lbl_pass.setStyleSheet("background-color: transparent;")
        cred_layout.addWidget(lbl_pass)

        self.pass_input = QLineEdit("")
        self.pass_input.setPlaceholderText("Enter Password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setFixedWidth(120)
        cred_layout.addWidget(self.pass_input)

        self.start_btn = QPushButton("▶ Start Auto-Refresh")
        self.start_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636; 
                color: #ffffff;
                border: 1px solid #2ea043; 
                font-weight: bold; 
                padding: 6px 12px;
                border-radius: 6px;
            }
            QPushButton:hover { 
                background-color: #2ea043; 
            }
            QPushButton:disabled { 
                background-color: #1b4d24; 
                color: #6e7681; 
                border-color: #21262d; 
            }
        """)
        self.start_btn.clicked.connect(self.start_monitoring)
        cred_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.setMinimumWidth(60)
        self.stop_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d; 
                color: #f85149;
                border: 1px solid #30363d; 
                font-weight: bold; 
                padding: 6px 12px;
                border-radius: 6px;
            }
            QPushButton:hover { 
                background-color: #361718; 
                border-color: #f85149; 
            }
            QPushButton:disabled { 
                background-color: #161b22; 
                color: #484f58; 
                border-color: #21262d; 
            }
        """)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        cred_layout.addWidget(self.stop_btn)

        top_bar_layout.addWidget(cred_group)

        self.global_alerts = GlobalAlertsWidget()
        top_bar_layout.addWidget(self.global_alerts, stretch=1)

        self.refresh_widget = RefreshStatusWidget()
        top_bar_layout.addWidget(self.refresh_widget)

        main_layout.addLayout(top_bar_layout)

        self.status_label = QLabel("Status: Idle. Enter credentials and click 'Start Auto-Refresh'.")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 11px; background-color: transparent;")
        main_layout.addWidget(self.status_label)

        cards_title = QLabel("Server Health Cards")
        cards_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        cards_title.setStyleSheet("color: #ffffff; margin-top: 4px; background-color: transparent;")
        main_layout.addWidget(cards_title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; }")

        scroll_content = QWidget()
        self.cards_grid = QGridLayout(scroll_content)
        self.cards_grid.setSpacing(10)
        self.cards_grid.setContentsMargins(2, 2, 2, 2)

        from config import SERVER_CONFIGS
        servers = list(SERVER_CONFIGS.keys())
        cols = 4

        for idx, srv in enumerate(servers):
            row = idx // cols
            col = idx % cols
            card = LparCardWidget(srv)
            self.card_widgets[srv] = card
            self.cards_grid.addWidget(card, row, col)

        for c in range(cols):
            self.cards_grid.setColumnStretch(c, 1)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)

    def start_monitoring(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text().strip()

        if not username or not password:
            self.status_label.setText("Error: Please enter both Username and Password.")
            self.status_label.setStyleSheet("color: #f85149; font-size: 11px; background-color: transparent;")
            return

        self.is_monitoring = True
        self.user_input.setEnabled(False)
        self.pass_input.setEnabled(False)
        
        self.start_btn.setEnabled(False)
        self.start_btn.setText("▶ Running...")
        
        self.stop_btn.setEnabled(True)

        self.refresh_widget.set_active_state(True)
        self.fetch_data()

    def stop_monitoring(self):
        self.is_monitoring = False
        self.timer.stop()

        self.user_input.setEnabled(True)
        self.pass_input.setEnabled(True)
        
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶ Start Auto-Refresh")
        
        self.stop_btn.setEnabled(False)

        self.refresh_widget.set_active_state(False)
        self.status_label.setText("Status: Monitoring stopped. Credentials unlocked for editing.")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 11px; background-color: transparent;")

    def fetch_data(self):
        self.timer.stop()

        if not self.is_monitoring:
            return

        vpn_ip = "189.88.18.66"
        if not is_vpn_connected(vpn_ip):
            self.stop_monitoring()

            # Reset all health cards to OFFLINE
            for srv_name, card in self.card_widgets.items():
                card.update_data({
                    "server": srv_name,
                    "status": "OFFLINE",
                    "cpu": 0.0,
                    "asp": 0.0,
                    "jobs": 0,
                    "subsystems": [],
                    "ports": []
                })

            # Reset global status counters
            self.global_alerts.update_summary([])

            self.status_label.setText("⚠️ Please check your VPN connection. Unable to reach the gateway.")
            self.status_label.setStyleSheet("color: #f85149; font-weight: bold; font-size: 11px; background-color: transparent;")
            
            QMessageBox.warning(
                self,
                "Connection not established",
                "Unable to reach VPN gateway.\nPlease connect to the VPN first."
            )
            return

        username = self.user_input.text().strip()
        password = self.pass_input.text().strip()

        self.status_label.setText("Status: Authenticating & fetching metrics concurrently...")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 11px; background-color: transparent;")

        self.thread = WorkerThread(username, password)
        self.thread.data_fetched.connect(self.update_cards)
        self.thread.start()

    def update_cards(self, data):
        self.global_alerts.update_summary(data)
        self.log_viewer_widget.load_log_history()

        auth_error_systems = []

        for sys_info in data:
            server_name = sys_info["server"]
            status = sys_info["status"]

            if status == "AUTH_ERROR":
                auth_error_systems.append(server_name)

            if server_name in self.card_widgets:
                self.card_widgets[server_name].update_data(sys_info)

        self.refresh_widget.update_timestamp()

        if auth_error_systems:
            err_servers_str = ", ".join(auth_error_systems)
            self.status_label.setText(
                f"Error: Authentication failed / User profile disabled on: {err_servers_str}. Retrying in 10s..."
            )
            self.status_label.setStyleSheet("color: #f85149; font-size: 11px; font-weight: bold; background-color: transparent;")
        else:
            self.status_label.setText("Status: Live Metrics Updated. Auto-refresh in 10s...")
            self.status_label.setStyleSheet("color: #8b949e; font-size: 11px; background-color: transparent;")

        if self.is_monitoring:
            self.timer.start(10000)