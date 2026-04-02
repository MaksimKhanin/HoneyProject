# admin_ui/core.py
"""Ядро Admin UI: auth, конфиг, константы. Без импортов страниц!"""

import os, yaml
from datetime import datetime
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from config_manager import get_config_manager
from logger import setup_logger

# === Конфигурация ===
CONFIG_PATH = os.getenv("CONFIG_PATH", "app/config.yaml")
CONFIG_MNG = get_config_manager(CONFIG_PATH)
CONFIG = CONFIG_MNG.get_config()

ADMIN_USER = os.getenv("UI_USER", "admin")
ADMIN_PASSWORD = os.getenv("UI_PASS", "admin")

logger = setup_logger(
    name="AdminUI",
    log_file=CONFIG['settings']['log_file'],
    level=CONFIG['settings']['log_level']
)

# === Константы ===
AVAILABLE_TIMEFRAMES = ["1m", "5m", "15m", "1h", "1d"]
TF_DEFAULTS = {
    "1m": {"history_depth_days": 7, "update_interval_minutes": 5},
    "5m": {"history_depth_days": 30, "update_interval_minutes": 15},
    "15m": {"history_depth_days": 60, "update_interval_minutes": 30},
    "1h": {"history_depth_days": 180, "update_interval_minutes": 60},
    "1d": {"history_depth_days": 365, "update_interval_minutes": 1440},
}

# === Auth ===
security = HTTPBasic()

def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != ADMIN_USER or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Access denied")
    return credentials.username

# === Конфиг хелперы ===
def load_config():
    return CONFIG_MNG.get_config() or {"instruments": []}

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return True

def get_tf_config(inst, tf_name):
    for tf in inst.get("timeframes", []):
        if tf.get("timeframe") == tf_name:
            return tf
    return None