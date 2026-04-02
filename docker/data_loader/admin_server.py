# === admin_server.py (добавь в loader/) ===
import threading
import uvicorn
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
import yaml, os, logging

logger = logging.getLogger(__name__)

# Импорт твоих модулей для работы с конфигом
from config_manager import load_config, save_config, get_tf_config  # адаптируй под свои имена

app = FastAPI()
security = HTTPBasic()
CONFIG_PATH = "/app/config.yaml"
AVAILABLE_TIMEFRAMES = ["1m", "5m", "15m", "1h", "1d"]
TF_DEFAULTS = {
    "1m": {"history_depth_days": 7, "update_interval_minutes": 5},
    "5m": {"history_depth_days": 30, "update_interval_minutes": 15},
    "15m": {"history_depth_days": 60, "update_interval_minutes": 30},
    "1h": {"history_depth_days": 180, "update_interval_minutes": 60},
    "1d": {"history_depth_days": 365, "update_interval_minutes": 1440},
}

def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != "admin" or credentials.password != os.getenv("ADMIN_PASSWORD", "change_me"):
        raise HTTPException(status_code=401, detail="Access denied")
    return credentials.username

# === Вставь сюда все эндпоинты из config_admin.py (dashboard, save, add) ===
# ... (код из предыдущих сообщений, но без restart_loader()) ...

def start_admin_server(host: str = "0.0.0.0", port: int = 8000):
    """Запускает админку в отдельном потоке"""
    logger.info(f"🚀 Запуск админки на {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning", access_log=False)

def run_admin_in_background():
    """Запускает админку в фоне, не блокируя основной поток"""
    thread = threading.Thread(target=start_admin_server, daemon=True)
    thread.start()
    return thread