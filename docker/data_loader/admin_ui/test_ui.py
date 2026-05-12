from main import start_admin_ui
import os
from dotenv import load_dotenv
from pathlib import Path

# Авто-загрузка .env из корня проекта
project_root = Path(__file__).parent.parent.parent.parent
print(project_root)

load_dotenv(project_root / ".env")

print(f"DB_HOST: {os.getenv('DB_HOST', 'НЕ ЗАГРУЖЕН')}")
print(f"TINKOFF_TOKEN: {'***' if os.getenv('TINKOFF_TOKEN') else 'НЕ ЗАГРУЖЕН'}")

start_admin_ui()