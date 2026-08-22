# ui/widgets.py
from PyQt6.QtCore import Qt, QRectF, QTimer, QDateTime
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QCursor
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QDialog, QVBoxLayout, 
    QHBoxLayout, QGridLayout, QApplication
)
from config import EXPECTED_SUBSYSTEMS, SERVICE_COMMANDS, SUBSYSTEM_COMMANDS


class RefreshStatusWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.header_label = QLabel("● Last Auto-Refresh")
        self.header_label.setStyleSheet("color: #3fb950; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.header_label)

        self.time_label = QLabel("--:-- --")
        self.time_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(self.time_label)

        self.date_label = QLabel("--- --, ----")
        self.date_label.setFont(QFont("Segoe UI", 9))
        self.date_label.setStyleSheet("color: #8b949e;")
        layout.addWidget(self.date_label)

    def set_active_state(self, active: bool):
        if active:
            self.header_label.setText("● Auto-Refresh Active")
            self.header_label.setStyleSheet("color: #3fb950; font-size: 11px; font-weight: bold;")
        else:
            self.header_label.setText("○ Auto-Refresh Paused")
            self.header_label.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: bold;")

    def update_timestamp(self):
        now = QDateTime.currentDateTime()
        self.time_label.setText(now.toString("hh:mm AP"))
        self.date_label.setText(now.toString("MMM d, yyyy"))


class CircularGauge(QWidget):
    def __init__(self, value, parent=None):
        super().__init__(parent)
        self.value = float(value)
        self.setFixedSize(80, 80)

    def set_value(self, value):
        self.value = float(value)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gauge_size = 64
        x = (self.width() - gauge_size) / 2
        y = (self.height() - gauge_size) / 2
        rect = QRectF(x, y, gauge_size, gauge_size)

        pen_width = 5.5

        bg_pen = QPen(QColor("#21262d"), pen_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(rect)

        color_hex = "#f85149" if self.value >= 90.0 else "#e3b341" if self.value >= 80.0 else "#388bfd"
        progress_pen = QPen(QColor(color_hex), pen_width)
        progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(progress_pen)

        capped_val = min(100.0, max(0.0, self.value))
        span_angle = int(-capped_val * 3.6 * 16)
        start_angle = 90 * 16
        painter.drawArc(rect, start_angle, span_angle)

        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text_rect = QRectF(x, y, gauge_size, gauge_size)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, f"{self.value:.1f}%")


class ItemDetailDialog(QDialog):
    def __init__(self, title_text, status_bool, command_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command Detail")
        self.setFixedSize(320, 200)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            QLabel { color: #c9d1d9; }
        """)

        self.reset_timer = QTimer(self)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self.reset_button_text)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title_label = QLabel(title_text)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(title_label)

        status_str = "UP" if status_bool else "DOWN"
        status_color = "#3fb950" if status_bool else "#f85149"
        status_label = QLabel(f'Status: <span style="color: {status_color}; font-weight: bold;">{status_str}</span>')
        status_label.setFont(QFont("Segoe UI", 9))
        layout.addWidget(status_label)

        cmd_label = QLabel(f'<span style="color: #8b949e;">Cmd:</span> <span style="color: #c9d1d9;">{command_text}</span>')
        cmd_label.setFont(QFont("Consolas", 9))
        cmd_label.setWordWrap(True)
        layout.addWidget(cmd_label)

        layout.addStretch()

        self.copy_btn = QPushButton("Copy Start Command")
        self.copy_btn.setFixedHeight(30)
        self.copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #ffffff;
            }
        """)
        self.copy_btn.clicked.connect(lambda: self.copy_command(command_text))
        layout.addWidget(self.copy_btn)

    def show_smart(self):
        """Displays dialog safely inside monitor boundaries."""
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
        screen_geo = screen.availableGeometry()

        dialog_w = self.width()
        dialog_h = self.height()

        # Target placement centered relative to cursor
        x = cursor_pos.x() - (dialog_w // 2)
        y = cursor_pos.y() - (dialog_h // 2)

        # Clamp positions within screen borders (10px margin)
        margin = 10
        x = max(screen_geo.left() + margin, min(x, screen_geo.right() - dialog_w - margin))
        y = max(screen_geo.top() + margin, min(y, screen_geo.bottom() - dialog_h - margin))

        self.move(x, y)
        self.exec()

    def copy_command(self, cmd):
        clipboard = QApplication.clipboard()
        clipboard.setText(cmd)
        self.copy_btn.setText("✓ Copied!")
        self.reset_timer.start(1500)

    def reset_button_text(self):
        if hasattr(self, "copy_btn") and self.copy_btn:
            self.copy_btn.setText("Copy Start Command")

    def reject(self):
        if hasattr(self, "reset_timer"):
            self.reset_timer.stop()
        super().reject()


class SubsystemBadge(QLabel):
    def __init__(self, name, is_up, parent=None):
        status_str = "UP" if is_up else "DOWN"
        super().__init__(f"● {name} ({status_str})", parent)
        self.name = name
        self.is_up = is_up
        self.command = SUBSYSTEM_COMMANDS.get(name, f"STRSBS SBSD({name})")

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(22)
        self.setMinimumWidth(110)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        if is_up:
            self.setStyleSheet("""
                QLabel {
                    background-color: #0d281e;
                    color: #3fb950;
                    border: 1px solid #1e4b33;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 9px;
                    padding: 2px 4px;
                }
                QLabel:hover {
                    background-color: #123b2c;
                    border-color: #2ea043;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background-color: #3c1618;
                    color: #f85149;
                    border: 1px solid #6e2024;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 9px;
                    padding: 2px 4px;
                }
                QLabel:hover {
                    background-color: #4e1c20;
                    border-color: #f85149;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            dialog = ItemDetailDialog(f"Subsystem: {self.name}", self.is_up, self.command, self)
            pos = QCursor.pos()
            dialog.move(pos.x() - 150, pos.y() - 100)
            dialog.exec()


class SubsystemGridWidget(QWidget):
    def __init__(self, server_name, active_subsystems, on_expand_callback=None, parent=None):
        super().__init__(parent)
        self.server_name = server_name
        self.on_expand_callback = on_expand_callback
        self.expected_subs = EXPECTED_SUBSYSTEMS.get(server_name, [])

        # Safely extract subsystem names if active_subsystems contains dictionaries
        names = [
            sub["name"] if isinstance(sub, dict) else sub
            for sub in active_subsystems
        ]
        self.active_set = set(names)

        running_count = sum(1 for s in self.expected_subs if s in self.active_set)
        total_count = len(self.expected_subs)
        self.all_healthy = running_count == total_count

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(4)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        header_container = QWidget()
        h_layout = QHBoxLayout(header_container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(8)

        header_color = "#3fb950" if self.all_healthy else "#f85149"
        self.header_label = QLabel(f"● {running_count} / {total_count} Active")
        self.header_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.header_label.setStyleSheet(f"color: {header_color}; background: transparent;")
        h_layout.addWidget(self.header_label)

        h_layout.addStretch()

        self.toggle_btn = QPushButton("Expand ▾")
        self.toggle_btn.setFixedSize(70, 22)
        self.toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 4px;
                font-size: 10px;
                padding: 0px;
            }
            QPushButton:hover {
                color: #ffffff;
                border-color: #58a6ff;
            }
        """)
        self.toggle_btn.clicked.connect(self.trigger_expand)
        h_layout.addWidget(self.toggle_btn)

        self.main_layout.addWidget(header_container)

    def trigger_expand(self):
        if self.on_expand_callback:
            self.on_expand_callback(self.server_name)


class ServiceBadge(QLabel):
    """Clickable badge displaying network service status, tooltips, and command dialogs."""
    def __init__(self, port_info, parent=None):
        if isinstance(port_info, dict):
            self.name = (
                port_info.get("name") or 
                port_info.get("service") or 
                port_info.get("port") or 
                port_info.get("label") or 
                "UNK"
            )
            self.is_up = port_info.get("is_up", port_info.get("status") == "UP")
            self.port_num = port_info.get("port", port_info.get("port_num", ""))
            self.desc = port_info.get("description", port_info.get("desc", f"{self.name} Service"))
            self.command = port_info.get(
                "command", 
                SERVICE_COMMANDS.get(self.name, SERVICE_COMMANDS.get(self.port_num, f"STRTCPSVR SERVER(*{self.name})"))
            )
        else:
            self.name = str(port_info)
            self.is_up = True
            self.port_num = ""
            self.desc = f"{self.name} Service"
            self.command = SERVICE_COMMANDS.get(self.name, f"STRTCPSVR SERVER(*{self.name})")

        status_symbol = "●" if self.is_up else "✖"
        super().__init__(f"{self.name} {status_symbol}", parent)

        self.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(22)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Rich text tooltip for hover details
        port_str = f" (Port {self.port_num})" if self.port_num else ""
        tooltip_html = (
            f"<b>Service:</b> {self.name}{port_str}<br>"
            f"<b>Status:</b> {'UP' if self.is_up else 'DOWN'}<br>"
            f"<b>Description:</b> {self.desc}<br>"
            f"<b>Command:</b> <code>{self.command}</code>"
        )
        self.setToolTip(tooltip_html)

        if self.is_up:
            self.setStyleSheet("""
                QLabel {
                    background-color: #0d2818;
                    color: #3fb950;
                    border: 1px solid #2ea043;
                    border-radius: 4px;
                    padding: 1px 2px;
                }
                QLabel:hover {
                    background-color: #123d24;
                    border-color: #3fb950;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background-color: #361718;
                    color: #f85149;
                    border: 1px solid #da3633;
                    border-radius: 4px;
                    padding: 1px 2px;
                }
                QLabel:hover {
                    background-color: #4d1f21;
                    border-color: #f85149;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            title = f"{self.name} Service"
            if self.port_num:
                title += f" (Port {self.port_num})"
            dialog = ItemDetailDialog(title, self.is_up, self.command, self)
            pos = QCursor.pos()
            dialog.move(pos.x() - 150, pos.y() - 100)
            dialog.exec()


class StatusBadgesWidget(QWidget):
    """Clean multi-column grid layout with clickable service badges."""
    def __init__(self, ports_data, parent=None):
        super().__init__(parent)
        
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setHorizontalSpacing(4)
        layout.setVerticalSpacing(4)

        cols = 5
        for idx, port in enumerate(ports_data):
            row = idx // cols
            col = idx % cols
            
            badge = ServiceBadge(port, parent=self)
            layout.addWidget(badge, row, col)
            
        for c in range(cols):
            layout.setColumnStretch(c, 1)


class CenteredCellWidget(QWidget):
    def __init__(self, child_widget, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(child_widget)