import paramiko
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTextEdit, QComboBox
)
from config import SERVER_CONFIGS


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
    def __init__(self, default_server="", default_cmd="", username="", password="", parent=None):
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

        layout = QVBoxLayout(self)

        h_layout1 = QHBoxLayout()
        h_layout1.addWidget(QLabel("Target LPAR:"))
        self.server_combo = QComboBox()
        self.server_combo.addItems(list(SERVER_CONFIGS.keys()))
        if default_server in SERVER_CONFIGS:
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
        host = SERVER_CONFIGS[server]["host"]
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