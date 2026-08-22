# worker.py

import os
import sys
import json
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import pyodbc
from PyQt6.QtCore import QThread, pyqtSignal
from config import SERVER_CONFIGS, MONITORED_PORTS


def get_logs_dir():
    """Returns absolute path to 'logs' directory relative to script or PyInstaller .exe."""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
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
                    print(f"Cleaned up old log file: {filename}")
            except Exception as e:
                print(f"Error parsing/deleting {filename}: {e}")


def save_metrics_to_log(results):
    """Appends fetched LPAR ODBC metrics to a daily JSON file inside the 'logs' folder."""
    logs_dir = get_logs_dir()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    filepath = os.path.join(logs_dir, f"lpar_history_{date_str}.json")

    formatted_records = []
    for sys_info in results:
        down_services = []
        if sys_info.get("ports"):
            down_services = [p["service"] for p in sys_info["ports"] if not p.get("is_up")]

        services_down_val = down_services if down_services else "None"
        server_name = sys_info.get("server")
        ip_addr = SERVER_CONFIGS.get(server_name, {}).get("host", "N/A")

        formatted_records.append({
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
        })

    entry = {
        "timestamp": timestamp_str,
        "records": formatted_records
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

    # Auto-clean logs older than 30 days inside 'logs' folder
    cleanup_old_logs(days_to_keep=30)


class WorkerThread(QThread):
    data_fetched = pyqtSignal(list)

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password

    def fetch_single_server(self, server, cfg):
        conn = None
        try:
            conn = pyodbc.connect(
                f"DRIVER={{IBM i Access ODBC Driver}};"
                f"SYSTEM={cfg['host']};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"SSL=0;"
                f"DATABASE={cfg['db']};"
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
                    WHERE TCP_STATE IN ('LISTEN', 'ESTABLISHED', '*UDP') 
                       OR PROTOCOL = 'UDP'
                    """
                )
                active_ports = {
                    int(r[0]) for r in cursor.fetchall() if r[0] is not None
                }

                for port, service in MONITORED_PORTS.items():
                    port_status_list.append(
                        {
                            "port": port,
                            "service": service,
                            "is_up": port in active_ports,
                        }
                    )
            except Exception:
                pass

            return {
                "server": server,
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
                return {
                    "server": server,
                    "status": "AUTH_ERROR",
                    "error": f"[{server}] {err_msg}",
                    "cpu": 0.0,
                    "asp": 0.0,
                    "jobs": 0,
                    "subsystems": [],
                    "ports": [],
                }

            return {
                "server": server,
                "status": "OFFLINE",
                "error": f"[{server}] {err_msg}",
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

    def run(self):
        results = []
        with ThreadPoolExecutor(max_workers=len(SERVER_CONFIGS)) as executor:
            future_to_server = {
                executor.submit(self.fetch_single_server, server, cfg): server
                for server, cfg in SERVER_CONFIGS.items()
            }
            for future in as_completed(future_to_server):
                try:
                    results.append(future.result())
                except Exception as exc:
                    server_name = future_to_server[future]
                    results.append({
                        "server": server_name,
                        "status": "OFFLINE",
                        "error": str(exc),
                        "cpu": 0.0,
                        "asp": 0.0,
                        "jobs": 0,
                        "subsystems": [],
                        "ports": []
                    })

        order = list(SERVER_CONFIGS.keys())
        results.sort(key=lambda x: order.index(x["server"]) if x["server"] in order else 99)

        save_metrics_to_log(results)
        self.data_fetched.emit(results)