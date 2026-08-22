import paramiko
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTextEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from config import SERVER_CONFIGS


class LparSettingsDialog(QDialog):
    """Modal dialog allowing users to dynamically configure LPAR IPs and Database names."""
    def __init__(self, current_configs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure LPAR Connections & Databases")
        self.resize(600, 380)
        self.configs = current_configs.copy()

        self.setStyleSheet("""
            QDialog { background-color: #161b22; color: #c9d1d9; }
            QLabel { color: #8b949e; font-weight: bold; }
            QTableWidget {
                background-color: #0d1117;
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
                padding: 6px;
            }
            QPushButton {
                background-color: #21262d;
                color: #ffffff;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #30363d; }
            QPushButton#saveBtn {
                background-color: #238636;
                border-color: #2ea043;
            }
            QPushButton#saveBtn:hover { background-color: #2ea043; }
        """)

        layout = QVBoxLayout(self)

        lbl = QLabel("Manage Server Connections (IP Address / Host & Database Name):")
        layout.addWidget(lbl)

        # Table View: Server Name, IP / Host, Database Name
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Server Name", "IP / Hostname", "Database Name"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        
        self.populate_table()
        layout.addWidget(self.table)

        # Action Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Add LPAR")
        add_btn.clicked.connect(self.add_row)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_row)

        save_btn = QPushButton("Save & Apply")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.save_and_close)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def populate_table(self):
        self.table.setRowCount(len(self.configs))
        for row, (srv_name, cfg) in enumerate(self.configs.items()):
            host = cfg.get("host", "") if isinstance(cfg, dict) else str(cfg)
            db = cfg.get("db", "*LOCAL") if isinstance(cfg, dict) else "*LOCAL"

            self.table.setItem(row, 0, QTableWidgetItem(srv_name))
            self.table.setItem(row, 1, QTableWidgetItem(host))
            self.table.setItem(row, 2, QTableWidgetItem(db))

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"LPAR0{row + 1}"))
        self.table.setItem(row, 1, QTableWidgetItem("192.168.1.1"))
        self.table.setItem(row, 2, QTableWidgetItem("*LOCAL"))

    def remove_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def save_and_close(self):
        new_configs = {}
        for row in range(self.table.rowCount()):
            srv_item = self.table.item(row, 0)
            host_item = self.table.item(row, 1)
            db_item = self.table.item(row, 2)

            if srv_item and host_item and srv_item.text().strip():
                srv_name = srv_item.text().strip().upper()
                host_val = host_item.text().strip()
                db_val = db_item.text().strip() if db_item and db_item.text().strip() else "*LOCAL"

                new_configs[srv_name] = {
                    "host": host_val,
                    "db": db_val
                }

        self.configs = new_configs
        self.accept()


class SSHRunnerThread(QThread):
    output_signal = pyqtSignal(str)

    def __init__(self, host, username, password, command):
        super().__init__()
        self.host = host
        self.username = username
        self.password = password
        self.command = command

    def run(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host, port=22, username=self.username, password=self.password, timeout=5)
            
            full_cmd = f"system \"{self.command}\""
            stdin, stdout, stderr = ssh.exec_command(full_cmd)
            
            out = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8')
            
            result = out if out else err if err else "Command executed with no output."
            self.output_signal.emit(f"=== Host: {self.host} ===\n{result}")
            ssh.close()
        except Exception as e:
            self.output_signal.emit(f"SSH Error on {self.host}: {str(e)}")


class CommandQuickActionDialog(QDialog):
    def __init__(self, default_server="", default_cmd="", username="", password="", server_configs=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command Quick-Action Panel")
        self.resize(550, 400)
        self.setStyleSheet("""
            QDialog { background-color: #161b22; color: #c9d1d9; }
            QLabel { color: #8b949e; font-weight: bold; }
            QLineEdit, QComboBox { background-color: #0d1117; border: 1px solid #30363d; color: #ffffff; padding: 6px; border-radius: 4px; }
            QTextEdit { background-color: #0d1117; border: 1px solid #30363d; color: #3fb950; font-family: Consolas; border-radius: 4px; }
            QPushButton { background-color: #238636; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #2ea043; }
        """)

        self.username = username
        self.password = password
        self.server_configs = server_configs or SERVER_CONFIGS

        layout = QVBoxLayout(self)

        h_layout1 = QHBoxLayout()
        h_layout1.addWidget(QLabel("Target LPAR:"))
        self.server_combo = QComboBox()
        self.server_combo.addItems(list(self.server_configs.keys()))
        if default_server in self.server_configs:
            self.server_combo.setCurrentText(default_server)
        h_layout1.addWidget(self.server_combo, stretch=1)
        layout.addLayout(h_layout1)

        h_layout2 = QHBoxLayout()
        h_layout2.addWidget(QLabel("CL Command:"))
        self.cmd_input = QLineEdit(default_cmd)
        h_layout2.addWidget(self.cmd_input, stretch=1)
        
        self.exec_btn = QPushButton("Execute via SSH")
        self.exec_btn.clicked.connect(self.execute_command)
        h_layout2.addWidget(self.exec_btn)
        layout.addLayout(h_layout2)

        layout.addWidget(QLabel("Execution Output Log:"))
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

    def execute_command(self):
        server = self.server_combo.currentText()
        cfg = self.server_configs.get(server, {})
        host = cfg.get("host", "") if isinstance(cfg, dict) else str(cfg)
        cmd = self.cmd_input.text().strip()

        if not cmd:
            self.output_text.append("Error: Command field cannot be empty.")
            return

        self.output_text.append(f"Connecting to {server} ({host}) to execute: {cmd}...")
        self.exec_btn.setEnabled(False)

        self.thread = SSHRunnerThread(host, self.username, self.password, cmd)
        self.thread.output_signal.connect(self.handle_output)
        self.thread.start()

    def handle_output(self, text):
        self.output_text.append(text)
        self.exec_btn.setEnabled(True)