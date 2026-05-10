# db/db_manager.py
import logging
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import List, Dict, Optional, Any

import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import pool

from logger import setup_logger
from constants import (
    DEFAULT_DB_SCHEMA, DEFAULT_DB_PORT, DEFAULT_TIMEZONE,
    SIGNAL_TYPES, TIMEFRAMES
)
import db_queries as Q


class DBManager:
    """
    Менеджер для работы с Postgres.

    Теперь все настройки передаются напрямую в __init__.
    Никаких магических конфигов — всё явно, как стоп-лосс на 2%.
    """

    def __init__(
            self,
            # 🗄️ Параметры БД
            db_host: str,
            db_name: str,
            db_user: str,
            db_password: str,
            db_port: int = DEFAULT_DB_PORT,
            db_schema: str = DEFAULT_DB_SCHEMA,

            # 🪵 Логирование
            log_file: str = "db_manager.log",
            log_level: str = "INFO",

            # 🌍 Таймзона
            timezone_name: str = DEFAULT_TIMEZONE,

            # 🔗 Пул подключений
            pool_minconn: int = 1,
            pool_maxconn: int = 3,
    ):
        # Сохраняем конфиг "на честном слове"
        self.db_config = {
            "host": db_host,
            "port": db_port,
            "name": db_name,
            "user": db_user,
            "password": db_password,
            "schema": db_schema,
        }

        self.pool_config = {
            "minconn": pool_minconn,
            "maxconn": pool_maxconn,
        }

        self.timezone_name = timezone_name

        # 🪵 Логгер
        self.logger = setup_logger("DBManager", log_file, log_level)

        # 🔗 Пул подключений
        self.conn_pool: Optional[pool.SimpleConnectionPool] = None
        self._init_pool()

        # ✅ Инициализация схемы (если нужно)
        self._init_schema()

        self.logger.info("DBManager инициализирован. Готов сосать... то есть, работать с БД.")

    # ===== Методы пула подключений =====

    def _init_pool(self):
        """Инициализация пула подключений."""
        try:
            schema = self.db_config['schema']
            self.conn_pool = pool.SimpleConnectionPool(
                minconn=self.pool_config['minconn'],
                maxconn=self.pool_config['maxconn'],
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['name'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                options=f'-c search_path={self.db_config["schema"]}'
            )
            self.logger.info(f"✅ Пул подключений создан (схема: {schema}).")
        except Exception as e:
            self.logger.error(f"❌ Пиздец при создании пула: {e}", exc_info=True)
            raise

    def _get_connection(self):
        """Получение подключения из пула."""
        if self.conn_pool:
            return self.conn_pool.getconn()
        # Фоллбэк: прямое подключение (если пул не создан)
        schema = self.db_config.get('schema', DEFAULT_DB_SCHEMA)
        return psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            database=self.db_config['name'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            options=f'-c search_path={schema}'
        )

    def _release_connection(self, conn):
        """Возврат подключения в пул."""
        if self.conn_pool:
            self.conn_pool.putconn(conn)

    def get_connection(self):
        """Context manager для подключения (удобно для with)."""
        conn = self._get_connection()
        return _ConnectionContext(conn, self._release_connection)

    # ===== Работа со схемой =====

    def _init_schema(self):
        """Создание схемы, если её нет."""
        schema = self.db_config.get('schema', DEFAULT_DB_SCHEMA)
        if schema == DEFAULT_DB_SCHEMA:
            return

        # Для создания схемы нужно подключение БЕЗ search_path
        conn = psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            database=self.db_config['name'],
            user=self.db_config['user'],
            password=self.db_config['password']
        )
        try:
            cur = conn.cursor()
            cur.execute(Q.CREATE_SCHEMA.format(schema=schema))
            cur.execute(Q.GRANT_SCHEMA.format(schema=schema, user=self.db_config['user']))
            cur.execute(Q.SET_SEARCH_PATH.format(schema=schema, user=self.db_config['user']))
            conn.commit()
            self.logger.info(f"✅ Схема '{schema}' создана/проверена.")
        except Exception as e:
            conn.rollback()
            self.logger.error(f"❌ Не удалось создать схему: {e}", exc_info=True)
            raise
        finally:
            cur.close()
            conn.close()

    # ===== Таймзоны =====

    def _get_tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    def _to_utc(self, dt: datetime) -> datetime:
        """Конвертирует datetime в UTC для хранения в БД."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _from_utc(self, dt: datetime) -> datetime:
        """Конвертирует UTC datetime из БД в локальный часовой пояс."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(self._get_tz())

    # ===== INSTRUMENTS =====

    def upsert_instruments_batch(self, instruments_list: List[Dict[str, Any]]) -> int:
        """Массовое сохранение инструментов."""
        self.logger.info(f"📦 Массовое сохранение {len(instruments_list)} инструментов...")
        conn = self._get_connection()
        saved_count = 0

        try:
            cur = conn.cursor()
            for inst in instruments_list:
                try:
                    cur.execute(Q.UPSERT_INSTRUMENT, (
                        inst['uid'],
                        inst['ticker'],
                        inst.get('name'),
                        inst.get('type'),
                        inst.get('class_code'),
                        inst.get('currency'),
                        inst.get('exchange'),
                        inst.get('min_price_increment'),
                        inst.get('lot'),
                        inst.get('api_trade_available')
                    ))
                    saved_count += 1
                except Exception as e:
                    self.logger.warning(f"⚠️ Не удалось сохранить {inst.get('ticker')}: {e}")
                    continue
            conn.commit()
            self.logger.info(f"✅ Сохранено {saved_count} из {len(instruments_list)} инструментов.")
            return saved_count
        except Exception as e:
            conn.rollback()
            self.logger.error(f"❌ Ошибка массового сохранения: {e}", exc_info=True)
            return 0
        finally:
            cur.close()
            self._release_connection(conn)

    def get_instrument_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Получить информацию об инструменте по тикеру."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(Q.GET_INSTRUMENT_BY_TICKER, (ticker,))
            result = cur.fetchone()
            if result:
                return dict(zip(
                    ["uid", "ticker", "name", "type", "class_code",
                     "currency", "exchange", "lot", "updated_at"],
                    result
                ))
            return None
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска инструмента {ticker}: {e}", exc_info=True)
            return None
        finally:
            cur.close()
            self._release_connection(conn)

    def get_uid_by_ticker(self, ticker: str) -> Optional[str]:
        """Получить UID инструмента по тикеру."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(Q.GET_UID_BY_TICKER, (ticker,))
            result = cur.fetchone()
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения UID: {e}", exc_info=True)
            return None
        finally:
            cur.close()
            self._release_connection(conn)

    # ===== CANDLES =====

    def save_candles(self, candles_list: List[Dict[str, Any]],
                     ticker: str, timeframe: str) -> int:
        """Массовое сохранение свечей с дедупликацией."""
        if not candles_list:
            self.logger.warning("⚠️ Пустой список свечей для сохранения.")
            return 0

        # Дедупликация по времени (UTC)
        unique_candles = {
            self._to_utc(candle['time']): candle
            for candle in candles_list
        }
        deduplicated = list(unique_candles.values())

        if len(deduplicated) < len(candles_list):
            removed = len(candles_list) - len(deduplicated)
            self.logger.warning(f"🗑️ Удалено {removed} дубликатов свечей.")

        if not deduplicated:
            return 0

        self.logger.info(f"💾 Сохранение {len(deduplicated)} свечей в БД...")
        conn = self._get_connection()

        try:
            cur = conn.cursor()
            values = [
                (
                    ticker, timeframe, self._to_utc(c['time']),
                    c['open'], c['high'], c['low'], c['close'], c['volume']
                )
                for c in deduplicated
            ]
            execute_values(
                cur, Q.UPSERT_CANDLES_BATCH, values, page_size=1000
            )
            saved_count = cur.rowcount
            conn.commit()
            self.logger.info(f"✅ Сохранено/обновлено {saved_count} свечей.")
            return saved_count
        except Exception as e:
            conn.rollback()
            self.logger.error(f"❌ Ошибка сохранения свечей: {e}", exc_info=True)
            return 0
        finally:
            cur.close()
            self._release_connection(conn)

    def get_last_candle_date(self, ticker: str, timeframe: str) -> Optional[datetime]:
        """Получить дату последней свечи."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(Q.GET_LAST_CANDLE_DATE, (ticker, timeframe))
            result = cur.fetchone()
            return result[0] if result and result[0] else None
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения последней даты: {e}", exc_info=True)
            return None
        finally:
            cur.close()
            self._release_connection(conn)

    def get_candles_count(self, ticker: str, timeframe: str) -> int:
        """Получить количество свечей."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(Q.GET_CANDLES_COUNT, (ticker, timeframe))
            result = cur.fetchone()
            return result[0] if result else 0
        except Exception as e:
            self.logger.error(f"❌ Ошибка подсчета свечей: {e}", exc_info=True)
            return 0
        finally:
            cur.close()
            self._release_connection(conn)

    def get_date_range(self, ticker: str, timeframe: str) -> tuple:
        """Получить диапазон дат."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(Q.GET_DATE_RANGE, (ticker, timeframe))
            result = cur.fetchone()
            return (result[0], result[1]) if result and result[0] else (None, None)
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения диапазона дат: {e}", exc_info=True)
            return (None, None)
        finally:
            cur.close()
            self._release_connection(conn)

    def get_recent_candles(self, ticker: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """Получить последние N свечей."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(Q.GET_RECENT_CANDLES, (ticker, timeframe, limit))
            results = cur.fetchall()
            return [
                {
                    'time': self._from_utc(row[0]),
                    'open': float(row[1]),
                    'high': float(row[2]),
                    'low': float(row[3]),
                    'close': float(row[4]),
                    'volume': row[5]
                }
                for row in results
            ]
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения свечей: {e}", exc_info=True)
            return []
        finally:
            cur.close()
            self._release_connection(conn)

    # ===== SIGNALS =====
    def save_signal(self,
                    ticker: str,
                    timeframe: str,
                    strategy: str,
                    signal: str,
                    price: float,
                    candle_time: datetime,
                    metadata: dict = None) -> bool:

        """Сохраняет торговый сигнал."""
        # Валидация (потому что я педант, блять)
        if signal not in SIGNAL_TYPES:
            self.logger.error(f"❌ Невалидный сигнал: {signal}")
            return False
        if timeframe not in TIMEFRAMES:
            self.logger.error(f"❌ Невалидный таймфрейм: {timeframe}")
            return False

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(Q.UPSERT_SIGNAL, (
                        ticker, timeframe, strategy, signal, price,
                        self._to_utc(candle_time),
                        json.dumps(metadata) if metadata else '{}'
                    ))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения сигнала {ticker}/{timeframe}: {e}")
            return False


    # ===== Утилиты =====

    def close(self):
        """Закрыть все подключения."""
        if self.conn_pool:
            self.conn_pool.closeall()
            self.logger.info("🔌 Все подключения к БД закрыты.")


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ===== INSTRUMENT CONFIG =====

    def init_instrument_config_table(self):
        """Создаёт таблицу instrument_config, если нет."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(Q.CREATE_INSTRUMENT_CONFIG_TABLE)
            conn.commit()
        self.logger.info("✅ Таблица instrument_config создана/проверена.")

    def get_enabled_instrument_configs(self) -> List[Dict[str, Any]]:
        """Получает все активные конфигурации инструментов из БД."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(Q.GET_ENABLED_INSTRUMENT_CONFIGS)
            columns = [desc[0] for desc in cur.description]
            results = []
            for row in cur.fetchall():
                config = dict(zip(columns, row))
                # Парсим JSONB поле
                if isinstance(config.get('strategy_params'), str):
                    import json
                    config['strategy_params'] = json.loads(config['strategy_params'])
                results.append(config)
            return results
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения конфигураций: {e}", exc_info=True)
            return []
        finally:
            cur.close()
            self._release_connection(conn)

    def get_instrument_config(self, ticker: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """
        Получает конфигурацию инструмента.

        direction извлекается из strategy_params JSON.
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(Q.GET_INSTRUMENT_CONFIG, (ticker, timeframe))
            row = cur.fetchone()

            if row:
                columns = [desc[0] for desc in cur.description]
                config = dict(zip(columns, row))

                # Парсим JSONB поле strategy_params
                if isinstance(config.get('strategy_params'), str):
                    import json
                    config['strategy_params'] = json.loads(config['strategy_params'])

                # 🔥 Извлекаем direction из strategy_params (с дефолтом)
                params = config.get('strategy_params') or {}
                config['direction'] = params.get('direction', 'ALL')

                # Гарантируем наличие флага live_trading_enabled
                config.setdefault('live_trading_enabled', False)

                return config
            return None
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения конфига {ticker}/{timeframe}: {e}")
            return None
        finally:
            cur.close()
            self._release_connection(conn)

    def upsert_instrument_config(
            self,
            ticker: str,
            timeframe: str,
            enabled: bool = True,
            history_depth_days: int = None,
            update_interval_minutes: int = None,
            strategy_name: str = "none",
            strategy_window: int = None,
            strategy_params: dict = None,
            live_trading_enabled: bool = False,  # 🔥 Отдельное поле в БД
            # 🔥 direction НЕ передаём отдельно — он внутри strategy_params!
    ) -> bool:
        """
        Вставляет или обновляет конфигурацию инструмента.

        Направление торговли (direction) должно быть передано ВНУТРЬ strategy_params:
            strategy_params={"period": 20, "direction": "BUY_ONLY"}
        """
        from constants import TIMEFRAMES, STRATEGY_DEFAULTS
        import json

        # Дефолты
        tf_defaults = TIMEFRAMES.get(timeframe, {})
        strat_defaults = STRATEGY_DEFAULTS.get(strategy_name, {}) if strategy_name != "none" else {}

        # 🔥 Объединяем параметры, сохраняя direction если он есть
        base_params = strat_defaults.get("params", {}).copy()
        if strategy_params:
            base_params.update(strategy_params)

        # Валидация direction (если указан)
        direction = base_params.get('direction', 'ALL')
        if direction not in ("BUY_ONLY", "SHORT_ONLY", "ALL"):
            self.logger.warning(f"⚠️ Неверное направление '{direction}', установлено 'ALL'")
            base_params['direction'] = 'ALL'

        config = {
            "history_depth_days": history_depth_days or tf_defaults.get("default_history_depth_days", 365),
            "update_interval_minutes": update_interval_minutes or tf_defaults.get("default_update_interval_min", 60),
            "strategy_window": strategy_window or strat_defaults.get("default_window", 20),
            "strategy_params": base_params,  # 🔥 direction уже внутри
            "live_trading_enabled": live_trading_enabled,
        }

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(Q.UPSERT_INSTRUMENT_CONFIG, (
                        ticker, timeframe, enabled,
                        config["history_depth_days"],
                        config["update_interval_minutes"],
                        strategy_name,
                        config["strategy_window"],
                        json.dumps(config["strategy_params"]),  # 🔥 direction внутри JSON
                        config["live_trading_enabled"],
                    ))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка upsert конфига {ticker}/{timeframe}: {e}")
            return False

    def toggle_instrument_enabled(self, ticker: str, timeframe: str, enabled: bool) -> bool:
        """Включает/выключает инструмент без изменения других параметров."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(Q.UPDATE_INSTRUMENT_ENABLED, (enabled, ticker, timeframe))
                    updated = cur.rowcount > 0
                conn.commit()
                if updated:
                    self.logger.info(f"✅ {ticker}/{timeframe}: enabled={enabled}")
                return updated
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления enabled {ticker}/{timeframe}: {e}")
            return False

    def get_instrument_config_stats(self) -> Dict[str, int]:
        """Статистика по конфигурациям."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(Q.GET_INSTRUMENT_CONFIG_STATS)
            row = cur.fetchone()
            if row:
                return {"total": row[0], "enabled": row[1], "with_strategy": row[2]}
            return {"total": 0, "enabled": 0, "with_strategy": 0}
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}
        finally:
            cur.close()
            self._release_connection(conn)

    def delete_instrument_config(self, ticker: str, timeframe: str) -> bool:
        """
        Физически удаляет конфигурацию инструмента.
        Возвращает True, если запись была удалена.
        """
        self.logger.info(f"🗑️ Удаление конфига: {ticker}/{timeframe}")

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Сначала удаляем связанные сигналы (чтобы не нарушать целостность)
                    cur.execute(Q.DELETE_SIGNALS_BY_TICKER_TF, (ticker, timeframe))
                    signals_deleted = cur.rowcount

                    # Затем удаляем сам конфиг
                    cur.execute(Q.DELETE_INSTRUMENT_CONFIG, (ticker, timeframe))
                    deleted = cur.rowcount > 0
                conn.commit()

                if deleted:
                    self.logger.info(f"✅ Удалено: {ticker}/{timeframe} (+ {signals_deleted} сигналов)")
                else:
                    self.logger.warning(f"⚠️ Не найдено для удаления: {ticker}/{timeframe}")
                return deleted
        except Exception as e:
            self.logger.error(f"❌ Ошибка удаления {ticker}/{timeframe}: {e}", exc_info=True)
            return False

    def delete_instrument_configs_by_ticker(self, ticker: str) -> int:
        """
        Удаляет все конфигурации и сигналы по тикеру.
        Возвращает количество удалённых конфигов.
        """
        self.logger.info(f"🗑️ Массовое удаление: {ticker} (все таймфреймы)")

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Удаляем сигналы по тикеру (все таймфреймы)
                    cur.execute("DELETE FROM signals WHERE ticker = %s", (ticker,))
                    signals_deleted = cur.rowcount

                    # Удаляем конфиги
                    cur.execute(Q.DELETE_INSTRUMENT_CONFIG_BY_TICKER, (ticker,))
                    deleted_count = cur.rowcount
                conn.commit()

                self.logger.info(f"✅ Удалено {ticker}: {deleted_count} конфигов, {signals_deleted} сигналов")
                return deleted_count
        except Exception as e:
            self.logger.error(f"❌ Ошибка массового удаления {ticker}: {e}", exc_info=True)
            return 0

    def init_metrics_table(self):
        """Создаёт таблицу metrics, если нет."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(Q.CREATE_METRICS_TABLE)
            conn.commit()
        self.logger.info("✅ Таблица metrics создана/проверена.")

    def get_latest_metrics(self, ticker: str, timeframe: str, limit: int = 1) -> List[Dict]:
        """Получает последние метрики для инструмента."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(Q.GET_METRICS_BY_TICKER_TF, (ticker, timeframe, limit))
            columns = [desc[0] for desc in cur.description]
            results = []
            for row in cur.fetchall():
                item = dict(zip(columns, row))
                if isinstance(item.get('metrics'), str):
                    import json
                    item['metrics'] = json.loads(item['metrics'])
                results.append(item)
            return results
        finally:
            cur.close()
            self._release_connection(conn)

    def get_metrics_summary(self, timeframe_filter: str = "all", limit: int = 50) -> List[Dict]:
        """Получает сводку последних метрик по инструментам."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(Q.GET_LATEST_METRICS, (timeframe_filter, timeframe_filter, limit))
            columns = [desc[0] for desc in cur.description]
            results = []
            for row in cur.fetchall():
                item = dict(zip(columns, row))
                if isinstance(item.get('metrics'), str):
                    import json
                    item['metrics'] = json.loads(item['metrics'])
                results.append(item)
            return results
        finally:
            cur.close()
            self._release_connection(conn)

    def save_metrics(
            self,
            ticker: str,
            timeframe: str,
            candle_time: datetime,
            metrics: Dict[str, Any]
    ) -> bool:
        """
        Сохраняет метрики для свечи в таблицу metrics.

        :param ticker: тикер инструмента
        :param timeframe: таймфрейм
        :param candle_time: время свечи (UTC)
        :param metrics: dict с метриками {"rsi_14": 45.2, "volatility_20": 0.023, ...}
        :return: True если успешно
        """
        import json

        if not metrics:
            self.logger.debug(f"⚠️ Пустые метрики для {ticker}/{timeframe}@{candle_time}")
            return False

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        Q.UPSERT_METRICS,
                        (
                            ticker,
                            timeframe,
                            self._to_utc(candle_time),  # Конвертируем в UTC для хранения
                            json.dumps(metrics)  # Сериализуем dict в JSONB
                        )
                    )
                conn.commit()
                self.logger.debug(f"✅ Сохранено метрик для {ticker}/{timeframe}@{candle_time}")
                return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения метрик {ticker}/{timeframe}: {e}", exc_info=True)
            return False


# ===== Вспомогательный класс для context manager =====
class _ConnectionContext:
    """Wrapper для подключения с авто-релизом."""

    def __init__(self, conn, release_callback):
        self.conn = conn
        self.release_callback = release_callback

    def __enter__(self):
        return self.conn

    def __exit__(self, *args):
        self.release_callback(self.conn)
        return False