# admin_ui/main.py
"""Точка входа Admin UI: создание app, подключение роутеров, жизненный цикл."""

import sys
import os
import asyncio
from contextlib import asynccontextmanager

# Добавляем корень проекта в path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fastapi import FastAPI
from admin_ui.core import logger, get_db, close_db, check_auth

# === Lifecycle manager для корректного закрытия БД ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ничего не делаем, DB инициализируется лениво
    logger.info("🚀 Admin UI запущен")
    yield
    # Shutdown: закрываем пул подключений
    logger.info("🔌 Закрытие соединений с БД...")
    close_db()
    logger.info("✅ Admin UI остановлен")

# === FastAPI app ===
app = FastAPI(lifespan=lifespan, title="Honey Loader Admin UI")

# === Подключаем роутеры ===
from admin_ui.pages import loader, strategies, portfolio

app.include_router(loader.router)
app.include_router(strategies.router)
app.include_router(portfolio.router)

# === Health check endpoint (для мониторинга) ===
@app.get("/health")
async def health_check():
    try:
        db = get_db()
        # Простой запрос для проверки подключения
        db.get_candles_count("SBER", "1h")
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": f"disconnected: {e}"}

# ===== GRACEFUL SHUTDOWN =====
@app.on_event("shutdown")
async def shutdown_event():
    """Корректное закрытие соединений при остановке сервера."""
    from core import close_db, close_broker
    close_db()
    close_broker()
    logger.info("✅ Admin UI остановлен, соединения закрыты")

# === Запуск ===
def start_admin_ui(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    logger.info(f"🌐 Admin UI доступен на http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="debug", access_log=False)

if __name__ == "__main__":
    start_admin_ui()