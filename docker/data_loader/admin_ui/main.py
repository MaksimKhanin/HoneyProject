# admin_ui/main.py
"""Точка входа Admin UI: создание app, подключение роутеров."""

import sys, os

# 🔥 Добавляем родителя в sys.path для импортов config_manager, logger
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fastapi import FastAPI
from admin_ui.core import logger  # ← импортируем из core, не создаём цикл

# === FastAPI app ===
app = FastAPI()

# === Подключаем роутеры страниц ===
# Импортируем ПОСЛЕ создания app, чтобы избежать цикла
from admin_ui.pages import loader, strategies, portfolio

app.include_router(loader.router)
app.include_router(strategies.router)
app.include_router(portfolio.router)

# === Запуск ===
def start_admin_ui(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    logger.info(f"🚀 Admin UI v4.1 (без циклических импортов) на {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info", access_log=False)

# if __name__ == "__main__":
#     start_admin_ui()