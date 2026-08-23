import os
import sys
import json
import re
import platform
from datetime import datetime, timedelta
import pyodbc
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
from config import SERVER_CONFIGS, MONITORED_PORTS, EXPECTED_PORTS


def get_logs_dir():
    """Return a per-user writable directory for history logs."""
    if platform.system() == "Windows":
        base_dir = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    elif platform.system() == "Darwin":
        base_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base_dir = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))
    base_dir = os.path.join(base_dir, "IBMi_Dashboard")
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def cleanup_old_logs(days_to_keep=30):
    """Deletes log files in the 'logs' folder older than days_to_keep."""
    logs_dir = get_logs_dir()
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    log_pattern = re.compile(r"^lpar_history_(\d{4}-\d{2}-\d{2})\.json$")

    if not os.path.exists(logs_dir):
        return

    for filename in os.listdir(logs_dir):
        match = log_pattern.match(filename)
        if match:
            file_date_str = match.group(1)
            try:
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                if file_date < cutoff_date:
                    file_path = os.path.join(logs_dir, filename)
                    os.remove(file_path)
            except Exception as e:
                print(f"Error parsing/deleting {filename}: {e}")


def save_single_lpar_log(sys_info, server_configs=None):
    """Appends a single LPAR result directly to the daily JSON history file upon worker completion."""
    logs_dir = get_logs_dir()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    filepath = os.path.join(logs_dir, f"lpar_history_{date_str}.json")

    configs = server_configs or SERVER_CONFIGS

    down_services = []
    if sys_info.get("ports"):
        down_services = [
            p.get("name") or p.get("service") 
            for p in sys_info["ports"] 
            if not p.get("is_up")
        ]

    services_down_val = down_services if down_services else "None"
    server_name = sys_info.get("server")
    
    cfg = configs.get(server_name, {})
    ip_addr = cfg.get("host", "N/A") if isinstance(cfg, dict) else str(cfg)

    record = {
        "timestamp": timestamp_str,
        "lpar": server_name,
        "server": server_name,
        "ip": ip_addr,
        "cpu": sys_info.get("cpu", 0.0),
        "asp": sys_info.get("asp", 0.0),
        "jobs": sys_info.get("jobs", 0),
        "status": sys_info.get("status", "OFFLINE"),
        "subsystems_summary": f"{len(sys_info.get('subsystems', []))} Active",
        "subsystems_detail": sys_info.get("subsystems", []),
        "services_down": services_down_val
    }

    entry = {
        "timestamp": timestamp_str,
        "records": [record]
    }

    existing_data = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
        except Exception:
            existing_data = []

    existing_data.append(entry)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2)
    except Exception as e:
        print(f"Failed to write log file: {e}")

    cleanup_old_logs(days_to_keep=30)


class LparWorkerSignals(QObject):
    """Signals for communicating LPAR query execution results safely to GUI widgets."""
    server_fetched = pyqtSignal(dict)


class SingleLparRunnable(QRunnable):
    """Concurrent worker task for fetching metrics from a single LPAR connection."""
    def __init__(self, server, cfg, username, password):
        super().__init__()
        self.server = server
        self.cfg = cfg
        self.username = username
        self.password = password
        self.signals = LparWorkerSignals()

    def run(self):
        conn = None
        host = self.cfg.get("host", "") if isinstance(self.cfg, dict) else str(self.cfg)
        db = self.cfg.get("db", "*LOCAL") if isinstance(self.cfg, dict) else "*LOCAL"

        try:
            driver = self.cfg.get("driver", "IBM i Access ODBC Driver") if isinstance(self.cfg, dict) else "IBM i Access ODBC Driver"
            conn = pyodbc.connect(
                f"DRIVER={{{driver}}};"
                f"SYSTEM={host};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"SSL=0;"
                f"DATABASE={db};"
                f"CONN_TIMEOUT=3;"
                f"QUERY_TIMEOUT=3;",
                timeout=3,
                autocommit=True
            )
            cursor = conn.cursor()

            active_jobs = 0
            asp_used = 0.0
            cpu_util = 0.0

            try:
                cursor.execute("SELECT COUNT(*) FROM TABLE(QSYS2.ACTIVE_JOB_INFO())")
                job_row = cursor.fetchone()
                if job_row and job_row[0] is not None:
                    active_jobs = job_row[0]

                cursor.execute("SELECT SYSTEM_ASP_USED FROM QSYS2.SYSTEM_STATUS_INFO")
                asp_row = cursor.fetchone()
                if asp_row and asp_row[0] is not None:
                    asp_used = float(round(asp_row[0], 2))
            except Exception:
                pass

            if asp_used == 0.0:
                try:
                    cursor.execute("SELECT PERCENT_PROCESSING_UNIT_USED FROM QSYS2.SYSTEM_ASP_INFO")
                    asp_row = cursor.fetchone()
                    if asp_row and asp_row[0] is not None:
                        asp_used = float(round(asp_row[0], 2))
                except Exception:
                    pass

            try:
                cursor.execute(
                    """
                    SELECT ROUND(AVERAGE_CPU_UTILIZATION, 2) AS CPU_UTILIZATION 
                    FROM TABLE(QSYS2.SYSTEM_ACTIVITY_INFO())
                    """
                )
                cpu_row = cursor.fetchone()
                if cpu_row and cpu_row[0] is not None:
                    cpu_util = float(cpu_row[0])
            except Exception:
                pass

            active_subsystems = []
            try:
                cursor.execute(
                    """
                    SELECT 
                        SUBSYSTEM_DESCRIPTION, 
                        STATUS, 
                        CURRENT_ACTIVE_JOBS, 
                        SIGNON_DEVICE_FILE_LIBRARY, 
                        TEXT_DESCRIPTION 
                    FROM QSYS2.SUBSYSTEM_INFO 
                    WHERE STATUS = 'ACTIVE'
                    """
                )
                for r in cursor.fetchall():
                    active_subsystems.append({
                        "name": str(r[0]).strip() if r[0] else "",
                        "status": str(r[1]).strip() if r[1] else "",
                        "active_jobs": r[2] if r[2] is not None else 0,
                        "library": str(r[3]).strip() if r[3] else "",
                        "description": str(r[4]).strip() if r[4] else ""
                    })
            except Exception:
                pass

            port_status_list = []
            try:
                cursor.execute(
                    """
                    SELECT LOCAL_PORT 
                    FROM QSYS2.NETSTAT_INFO 
                    WHERE TCP_STATE IN ('LISTEN')
                    """
                )
                active_ports = {
                    int(r[0]) for r in cursor.fetchall() if r[0] is not None and str(r[0]).isdigit()
                }

                target_ports = EXPECTED_PORTS.get(self.server, [])
                if not target_ports and isinstance(MONITORED_PORTS, dict):
                    target_ports = [{"port": p, "name": s} for p, s in MONITORED_PORTS.items()]

                for p_info in target_ports:
                    p_num = p_info.get("port") if isinstance(p_info, dict) else p_info
                    p_name = p_info.get("name", f"PORT_{p_num}") if isinstance(p_info, dict) else str(p_num)
                    
                    if str(p_num).isdigit():
                        port_status_list.append({
                            "port": int(p_num),
                            "name": p_name,
                            "service": p_name,
                            "is_up": int(p_num) in active_ports
                        })
            except Exception:
                pass

            result = {
                "server": self.server,
                "status": "ONLINE",
                "cpu": cpu_util,
                "asp": asp_used,
                "jobs": active_jobs,
                "subsystems": active_subsystems,
                "ports": port_status_list,
            }

        except Exception as e:
            err_msg = str(e)
            if any(k in err_msg.lower() for k in ["28000", "cwbsy0011", "disabled", "password", "authentication"]):
                result = {
                    "server": self.server,
                    "status": "AUTH_ERROR",
                    "error": f"[{self.server}] {err_msg}",
                    "cpu": 0.0,
                    "asp": 0.0,
                    "jobs": 0,
                    "subsystems": [],
                    "ports": [],
                }
            else:
                result = {
                    "server": self.server,
                    "status": "OFFLINE",
                    "error": f"[{self.server}] {err_msg}",
                    "cpu": 0.0,
                    "asp": 0.0,
                    "jobs": 0,
                    "subsystems": [],
                    "ports": [],
                }
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        save_single_lpar_log(result)
        self.signals.server_fetched.emit(result)