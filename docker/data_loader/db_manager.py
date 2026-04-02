import os
import logging
import json
from datetime import datetime
from datetime import timezone
from zoneinfo import ZoneInfo
from typing import List, Dict, Optional, Any
import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import pool

from logger import setup_logger
from config_manager import get_config_manager


class DBManager:
    """
    Менеджер для работы с Postgres.
    Использует ConfigManager для получения настроек.
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config_manager = get_config_manager(config_path)
        self.config = self.config_manager.get_config()

        self.logger = setup_logger(
            "DBManager",
            self.config['settings']['log_file'],
            self.config['settings']['log_level']
        )

        self.db_config = self.config['database']
        self.conn_pool = None
        self._init_pool()

        self.logger.info("DBManager инициализирован успешно.")

    def reload_config(self):
        """Перезагрузка конфига (вызывается при изменении)."""
        self.config = self.config_manager.get_config()
        self.db_config = self.config['database']
        self.logger.info("Конфиг базы данных обновлен")

    def _init_pool(self):
        """Инициализация пула подключений."""
        try:
            schema = self.db_config.get('schema', 'public')

            self.conn_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=3,
                host=self.db_config['host'],
                port=self.db_config.get('port', 5432),
                database=self.db_config['name'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                options=f'-c search_path={schema}'
            )
            self.logger.info(f"Пул подключений создан (схема: {schema}).")
        except Exception as e:
            self.logger.error(f"Ошибка создания пула подключений: {e}", exc_info=True)
            raise

    def _get_connection(self):
        """Получение подключения из пула."""
        if self.conn_pool:
            return self.conn_pool.getconn()
        else:
            schema = self.db_config.get('schema', 'public')
            return psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config.get('port', 5432),
                database=self.db_config['name'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                options=f'-c search_path={schema}'
            )

    def _release_connection(self, conn):
        """Возврат подключения в пул."""
        if self.conn_pool:
            self.conn_pool.putconn(conn)

    def _init_schema(self):
        """Создание схемы, если её нет."""
        schema = self.db_config.get('schema', 'public')

        if schema == 'public':
            return

        conn = psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config.get('port', 5432),
            database=self.db_config['name'],
            user=self.db_config['user'],
            password=self.db_config['password']
        )

        try:
            cur = conn.cursor()
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            cur.execute(f"GRANT ALL ON SCHEMA {schema} TO {self.db_config['user']}")
            cur.execute(f"ALTER USER {self.db_config['user']} SET search_path TO {schema}, public")
            conn.commit()
            self.logger.info(f"Схема '{schema}' создана/проверена.")
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Ошибка создания схемы: {e}", exc_info=True)
            raise
        finally:
            cur.close()
            conn.close()

    def _get_tz(self) -> ZoneInfo:
        """Возвращает объект таймзоны из конфига."""
        tz_name = self.config.get('settings', {}).get('timezone', 'UTC')
        return ZoneInfo(tz_name)

    def _to_utc(self, dt: datetime) -> datetime:
        """Конвертирует datetime в UTC для хранения в БД."""
        if dt.tzinfo is None:
            # Считаем, что naive datetime — это уже UTC от брокера
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _from_utc(self, dt: datetime) -> datetime:
        """Конвертирует UTC datetime из БД в локальный часовой пояс."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(self._get_tz())

    def upsert_instruments_batch(self, instruments_list: List[Dict[str, Any]]) -> int:
        """Массовое сохранение инструментов."""
        self.logger.info(f"Массовое сохранение {len(instruments_list)} инструментов...")

        conn = self._get_connection()
        saved_count = 0

        try:
            cur = conn.cursor()

            for inst in instruments_list:
                try:
                    cur.execute("""
                        INSERT INTO instruments 
                           (uid, 
                            ticker, 
                            name, 
                            type, 
                            class_code, 
                            currency, 
                            exchange, 
                            min_price_increment, 
                            lot,
                            api_trade_available, 
                            updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,  %s, NOW())
                        ON CONFLICT (uid) DO UPDATE SET
                            ticker = EXCLUDED.ticker,
                            name = EXCLUDED.name,
                            type = EXCLUDED.type,
                            class_code = EXCLUDED.class_code,
                            currency = EXCLUDED.currency,
                            exchange = EXCLUDED.exchange,
                            min_price_increment = EXCLUDED.min_price_increment,
                            lot = EXCLUDED.lot,
                            api_trade_available = EXCLUDED.api_trade_available,
                            updated_at = NOW()
                    """, (
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
                    self.logger.warning(f"Не удалось сохранить {inst.get('ticker')}: {e}")
                    continue

            conn.commit()
            self.logger.info(f"Сохранено {saved_count} из {len(instruments_list)} инструментов.")
            return saved_count

        except Exception as e:
            conn.rollback()
            self.logger.error(f"Ошибка массового сохранения: {e}", exc_info=True)
            return 0
        finally:
            cur.close()
            self._release_connection(conn)

    def save_candles(self, candles_list: List[Dict[str, Any]],
                     ticker: str, timeframe: str) -> int:
        """Массовое сохранение свечей с дедупликацией."""
        if not candles_list:
            self.logger.warning("Пустой список свечей для сохранения.")
            return 0

        # Дедупликация
        unique_candles = {}
        for candle in candles_list:
            time_key = self._to_utc(candle['time'])
            unique_candles[time_key] = candle

        deduplicated = list(unique_candles.values())

        if len(deduplicated) < len(candles_list):
            removed = len(candles_list) - len(deduplicated)
            self.logger.warning(f"Удалено {removed} дубликатов свечей перед вставкой.")

        if not deduplicated:
            self.logger.warning("После дедупликации список пуст.")
            return 0

        self.logger.info(f"Сохранение {len(deduplicated)} свечей в БД...")

        conn = self._get_connection()
        saved_count = 0

        try:
            cur = conn.cursor()

            values = []
            for candle in deduplicated:
                values.append((
                    ticker,
                    timeframe,
                    candle['time'],
                    candle['open'],
                    candle['high'],
                    candle['low'],
                    candle['close'],
                    candle['volume']
                ))

            execute_values(
                cur,
                """
                INSERT INTO candles 
                (ticker, timeframe, time, open, high, low, close, volume)
                VALUES %s
                ON CONFLICT (ticker, timeframe, time) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
                """,
                values,
                page_size=1000
            )

            saved_count = cur.rowcount
            conn.commit()

            self.logger.info(f"✅ Сохранено/обновлено {saved_count} свечей.")
            return saved_count

        except Exception as e:
            conn.rollback()
            self.logger.error(f"Ошибка сохранения свечей: {e}", exc_info=True)
            return 0
        finally:
            cur.close()
            self._release_connection(conn)

    def get_last_candle_date(self, ticker: str, timeframe: str) -> Optional[datetime]:
        """Получить дату последней свечи."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()

            cur.execute("""
                SELECT MAX(time) FROM candles
                WHERE ticker = %s AND timeframe = %s
            """, (ticker, timeframe))

            result = cur.fetchone()

            if result and result[0]:
                return result[0]
            else:
                return None

        except Exception as e:
            self.logger.error(f"Ошибка получения последней даты: {e}", exc_info=True)
            return None
        finally:
            cur.close()
            self._release_connection(conn)

    def get_instrument_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Получить информацию об инструменте по тикеру."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()

            cur.execute("""
                SELECT uid, ticker, name, type, class_code, currency, exchange, lot, updated_at
                FROM instruments
                WHERE ticker = %s
            """, (ticker,))

            result = cur.fetchone()

            if result:
                return {
                    'uid': result[0],
                    'ticker': result[1],
                    'name': result[2],
                    'type': result[3],
                    'class_code': result[4],
                    'currency': result[5],
                    'exchange': result[6],
                    'lot': result[7],
                    'updated_at': result[8]
                }
            else:
                return None

        except Exception as e:
            self.logger.error(f"Ошибка поиска инструмента {ticker}: {e}", exc_info=True)
            return None
        finally:
            cur.close()
            self._release_connection(conn)

    def get_candles_count(self, ticker: str, timeframe: str) -> int:
        """Получить количество свечей."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()

            cur.execute("""
                SELECT COUNT(*) FROM candles
                WHERE ticker = %s AND timeframe = %s
            """, (ticker, timeframe))

            result = cur.fetchone()
            return result[0] if result else 0

        except Exception as e:
            self.logger.error(f"Ошибка подсчета свечей: {e}", exc_info=True)
            return 0
        finally:
            cur.close()
            self._release_connection(conn)

    def get_date_range(self, ticker: str, timeframe: str) -> tuple:
        """Получить диапазон дат."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()

            cur.execute("""
                SELECT MIN(time), MAX(time) FROM candles
                WHERE ticker = %s AND timeframe = %s
            """, (ticker, timeframe))

            result = cur.fetchone()

            if result and result[0]:
                return (result[0], result[1])
            else:
                return (None, None)

        except Exception as e:
            self.logger.error(f"Ошибка получения диапазона дат: {e}", exc_info=True)
            return (None, None)
        finally:
            cur.close()
            self._release_connection(conn)

    def get_recent_candles(self, ticker: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """Получить последние N свечей."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()

            cur.execute("""
                SELECT time, open, high, low, close, volume FROM candles
                WHERE ticker = %s AND timeframe = %s
                ORDER BY time DESC
                LIMIT %s
            """, (ticker, timeframe, limit))

            results = cur.fetchall()

            candles = []
            for row in results:
                candles.append({
                    'time': self._from_utc(row[0]),
                    'open': float(row[1]),
                    'high': float(row[2]),
                    'low': float(row[3]),
                    'close': float(row[4]),
                    'volume': row[5]
                })

            return candles

        except Exception as e:
            self.logger.error(f"Ошибка получения свечей: {e}", exc_info=True)
            return []
        finally:
            cur.close()
            self._release_connection(conn)

    def create_signals_table(self):
        """Создает таблицу для торговых сигналов."""
        query = """
        CREATE TABLE IF NOT EXISTS signals (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            strategy VARCHAR(50) NOT NULL,
            signal VARCHAR(10) NOT NULL,  -- BUY, SELL, HOLD, ERROR
            price NUMERIC(20, 8) NOT NULL,
            candle_time TIMESTAMP NOT NULL,  -- время свечи, на которой сработал сигнал
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}',  -- доп. данные: RSI=28.5, SMA_fast=150.2 и т.д.

            -- Уникальность: один сигнал на свечу + стратегию
            UNIQUE(ticker, timeframe, strategy, candle_time)
        );

        -- Индексы для быстрых выборок
        CREATE INDEX IF NOT EXISTS idx_signals_ticker_tf 
            ON signals(ticker, timeframe);
        CREATE INDEX IF NOT EXISTS idx_signals_time 
            ON signals(candle_time DESC);
        CREATE INDEX IF NOT EXISTS idx_signals_active 
            ON signals(ticker, timeframe, strategy) WHERE signal IN ('BUY', 'SELL');
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
            conn.commit()

    def save_signal(self, ticker: str, timeframe: str, strategy: str,
                    signal: str, price: float, candle_time: datetime,
                    metadata: dict = None) -> bool:
        """Сохраняет торговый сигнал. Возвращает True если успешно."""
        query = """
        INSERT INTO signals (ticker, timeframe, strategy, signal, price, candle_time, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker, timeframe, strategy, candle_time) 
        DO UPDATE SET 
            signal = EXCLUDED.signal,
            price = EXCLUDED.price,
            created_at = CURRENT_TIMESTAMP
        RETURNING id
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        ticker, timeframe, strategy, signal, price,
                        candle_time, json.dumps(metadata) if metadata else '{}'
                    ))
                    conn.commit()
                    return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения сигнала {ticker}/{timeframe}: {e}")
            return False

    def get_uid_by_ticker(self, ticker: str) -> Optional[str]:
        """Получить UID инструмента по тикеру."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()

            cur.execute("""
                SELECT uid FROM instruments
                WHERE ticker = %s
            """, (ticker,))

            result = cur.fetchone()

            if result:
                return result[0]
            else:
                return None

        except Exception as e:
            self.logger.error(f"Ошибка получения UID: {e}", exc_info=True)
            return None
        finally:
            cur.close()
            self._release_connection(conn)

    def close(self):
        """Закрыть все подключения."""
        if self.conn_pool:
            self.conn_pool.closeall()
            self.logger.info("Все подключения к БД закрыты.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()