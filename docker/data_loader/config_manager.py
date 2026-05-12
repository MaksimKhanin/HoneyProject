import os
import yaml
import hashlib
import logging
import threading
import signal
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import re
from logger import setup_logger

from dotenv import load_dotenv
from pathlib import Path

# Авто-загрузка .env из корня проекта
project_root = Path(__file__).parent.parent.parent
print(project_root)

load_dotenv(project_root / ".env")

print(f"DB_HOST: {os.getenv('DB_HOST', 'НЕ ЗАГРУЖЕН')}")
print(f"TINKOFF_TOKEN: {'***' if os.getenv('TINKOFF_TOKEN') else 'НЕ ЗАГРУЖЕН'}")

def _substitute_env_variables(config: Any) -> Any:
    """
    Рекурсивно заменяет ${VAR_NAME} на значения из os.environ.
    Поддерживает формат ${VAR:-default} для дефолтных значений.
    """
    if isinstance(config, dict):
        return {k: _substitute_env_variables(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_substitute_env_variables(item) for item in config]
    elif isinstance(config, str):
        # Паттерн для ${VAR} или ${VAR:-default}
        pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'

        def replace(match):
            var_name = match.group(1)
            default = match.group(2)
            return os.environ.get(var_name, default if default is not None else match.group(0))

        return re.sub(pattern, replace, config)
    else:
        return config


class ConfigManager:
    """
    Менеджер конфигурации с поддержкой hot reload.
    Singleton паттерн + thread-safe.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: str = "config.yaml"):
        # Инициализация только один раз (singleton)
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True
        self.config_path = config_path
        self._config = None
        self._config_hash = None
        self._lock = threading.RLock()
        self._reload_callbacks: List[Callable] = []
        self._running = False
        self._watcher_thread = None

        # === ВАЖНО: Создаем временный логгер ДО загрузки конфига ===
        # Используем дефолтные настройки, которые потом перезапишутся
        self.logger = logging.getLogger("ConfigManager")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(levelname)s | %(name)s | %(message)s'))
            self.logger.addHandler(handler)

        # Теперь можно безопасно грузить конфиг (логгер уже есть)
        self.reload_config()

        # Пересоздаем логгер с правильными настройками из конфига
        self._setup_proper_logger()

        self.logger.info(f"ConfigManager инициализирован: {config_path}")

    def _setup_proper_logger(self):
        """Пересоздает логгер с настройками из конфига."""
        try:
            log_file = self._config.get('settings', {}).get('log_file', 'logs/app.log')
            log_level = self._config.get('settings', {}).get('log_level', 'INFO')

            # Пересоздаем логгер с правильными настройками
            self.logger = setup_logger(
                "ConfigManager",
                log_file,
                log_level
            )
        except Exception as e:
            # Фоллбэк: оставляем базовый логгер
            self.logger.warning(f"Не удалось настроить логгер из конфига: {e}")

    def _compute_hash(self, filepath: str) -> str:
        """Вычисляет MD5 хэш файла для детекта изменений."""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def reload_config(self) -> bool:
        """
        Перезагружает конфиг из файла.
        Возвращает True, если конфиг изменился.
        """
        with self._lock:
            try:
                new_hash = self._compute_hash(self.config_path)

                if new_hash == self._config_hash:
                    return False

                with open(self.config_path, 'r', encoding='utf-8') as f:
                    new_config = yaml.safe_load(f)
                new_config = _substitute_env_variables(new_config)

                old_config = self._config
                self._config = new_config
                self._config_hash = new_hash

                # Логгер может ещё не быть настроен — проверяем
                if hasattr(self, 'logger') and self.logger:
                    self.logger.info("✅ Конфиг перезагружен")
                else:
                    print(f"✅ Конфиг перезагружен (логгер ещё не инициализирован)")

                # Вызываем callback'и
                for callback in self._reload_callbacks:
                    try:
                        callback(new_config, old_config)
                    except Exception as e:
                        if hasattr(self, 'logger') and self.logger:
                            self.logger.error(f"Ошибка callback при reload: {e}")
                        else:
                            print(f"❌ Ошибка callback: {e}")

                return True

            except Exception as e:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.error(f"Ошибка перезагрузки конфига: {e}", exc_info=True)
                else:
                    print(f"❌ Ошибка перезагрузки конфига: {e}")
                return False

    def get_config(self) -> Dict:
        """Thread-safe получение конфига."""
        with self._lock:
            return self._config.copy() if self._config else {}

    def get_instruments(self, enabled_only: bool = True) -> List[Dict]:
        """
        Получение списка инструментов с таймфреймами.
        Возвращает плоский список: каждый (ticker, timeframe) — отдельная запись.
        """
        with self._lock:
            if not self._config:
                return []

            instruments = []

            for inst in self._config.get('instruments', []):
                if enabled_only and not inst.get('enabled', True):
                    continue

                ticker = inst['ticker']

                for tf in inst.get('timeframes', []):
                    if enabled_only and not tf.get('enabled', True):
                        continue

                    instruments.append({
                        'ticker': ticker,
                        'timeframe': tf['timeframe'],

                        # Параметры загрузки
                        'history_depth_days': tf.get('history_depth_days',
                                                     self._config.get('settings', {}).get('default_history_depth_days',
                                                                                          365)),
                        'update_interval_minutes': tf.get('update_interval_minutes', 60),

                        # 🔥 СТРАТЕГИЯ — ДОБАВЛЯЕМ ЭТИ ДВЕ СТРОКИ!
                        'strategy': tf.get('strategy', 'none'),
                        'strategy_window': tf.get('strategy_window'),  # опционально

                        # Флаги
                        'enabled': tf.get('enabled', True)
                    })

            return instruments

    def register_reload_callback(self, callback: Callable):
        """Регистрация callback'а для уведомления об изменении конфига."""
        self._reload_callbacks.append(callback)

    def start_watcher(self):
        """Запуск фонового потока для авто-детекта изменений конфига."""
        if self._running:
            return

        self._running = True
        self._watcher_thread = threading.Thread(target=self._watch_config, daemon=True)
        self._watcher_thread.start()
        if hasattr(self, 'logger') and self.logger:
            self.logger.info("👁️ Watcher конфига запущен")

    def stop_watcher(self):
        """Остановка watcher."""
        self._running = False
        if self._watcher_thread:
            self._watcher_thread.join(timeout=5)
        if hasattr(self, 'logger') and self.logger:
            self.logger.info("Watcher конфига остановлен")

    def _watch_config(self):
        """Фоновый поток для проверки изменений конфига."""
        while self._running:
            try:
                interval = self._config.get('settings', {}).get('config_reload_interval_seconds',
                                                                60) if self._config else 60

                for _ in range(interval):
                    if not self._running:
                        break
                    threading.Event().wait(1)

                if self._running:
                    self.reload_config()

            except Exception as e:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.error(f"Ошибка watcher: {e}")

    def setup_signal_handler(self):
        """Настройка SIGHUP для принудительной перезагрузки конфига."""

        def sighup_handler(signum, frame):
            if hasattr(self, 'logger') and self.logger:
                self.logger.info("📡 Получен SIGHUP — перезагрузка конфига...")
            self.reload_config()

        try:
            signal.signal(signal.SIGHUP, sighup_handler)
            if hasattr(self, 'logger') and self.logger:
                self.logger.info("SIGHUP handler установлен (kill -HUP <pid>)")
        except AttributeError:
            # SIGHUP может не поддерживаться на Windows
            if hasattr(self, 'logger') and self.logger:
                self.logger.warning("SIGHUP не поддерживается на этой платформе")


# Глобальный инстанс для удобного доступа
_config_manager_instance: Optional[ConfigManager] = None


def get_config_manager(config_path: str = "config.yaml") -> ConfigManager:
    """Получить singleton инстанс ConfigManager."""
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager(config_path)
    return _config_manager_instance