import os
import sys
import json

def get_config_path():
    """Returns absolute path to 'config.json' in the application base directory."""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "config.json")

# Default values used as fallback or initial setup
DEFAULT_SERVER_CONFIGS = {}

DEFAULT_EXPECTED_SUBSYSTEMS = {}

DEFAULT_EXPECTED_PORTS = {}

def load_server_configs():
    """Loads server configurations from config.json or returns default."""
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("SERVER_CONFIGS", DEFAULT_SERVER_CONFIGS)
        except Exception as e:
            print(f"Error loading config.json: {e}")
    return DEFAULT_SERVER_CONFIGS.copy()

def load_expected_subsystems():
    """Loads expected subsystems from config.json or returns default."""
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("EXPECTED_SUBSYSTEMS", DEFAULT_EXPECTED_SUBSYSTEMS)
        except Exception as e:
            print(f"Error loading config.json: {e}")
    return DEFAULT_EXPECTED_SUBSYSTEMS.copy()

def load_expected_ports():
    """Loads expected ports from config.json or returns default."""
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("EXPECTED_PORTS", DEFAULT_EXPECTED_PORTS)
        except Exception as e:
            print(f"Error loading config.json: {e}")
    return DEFAULT_EXPECTED_PORTS.copy()

def save_all_configs(server_configs, expected_subsystems=None, expected_ports=None):
    """Saves updated SERVER_CONFIGS, EXPECTED_SUBSYSTEMS, and EXPECTED_PORTS directly to config.json."""
    config_path = get_config_path()
    if expected_subsystems is None:
        expected_subsystems = load_expected_subsystems()
    if expected_ports is None:
        expected_ports = load_expected_ports()

    data = {
        "SERVER_CONFIGS": server_configs,
        "EXPECTED_SUBSYSTEMS": expected_subsystems,
        "EXPECTED_PORTS": expected_ports
    }

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error writing to config.json: {e}")
        return False

# Initialize module-level dictionaries dynamically
SERVER_CONFIGS = load_server_configs()
EXPECTED_SUBSYSTEMS = load_expected_subsystems()
EXPECTED_PORTS = load_expected_ports()

MONITORED_PORTS = {
    
}

SERVICE_COMMANDS = {
    21: "STRTCPSVR SERVER(*FTP)",
    22: "STRTCPSVR SERVER(*SSHD)",
    23: "STRTCPSVR SERVER(*TELNET)",
    25: "STRTCPSVR SERVER(*SMTP)",
    445: "STRTCPSVR SERVER(*NETS)",
    992: "STRTCPSVR SERVER(*ALL)",
    2001: "STRTCPSVR SERVER(*HTTP)",
    2002: "STRTCPSVR SERVER(*HTTP)",
    31111: "STRNETMAN",
    31114: "STRNETMAN",
}

SUBSYSTEM_COMMANDS = {
    
}