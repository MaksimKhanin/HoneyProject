# components/price_loader.py
"""
🕯️ PriceLoader: компонент для загрузки свечей.
Отвечает ТОЛЬКО за: получение UID → загрузка от брокера → сохранение в БД.
Никакой логики стратегий, никаких конфигов — только работа с данными.
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from constants import TIMEFRAMES, MAX_CANDLES_IN_MEMORY, BATCH_SAVE_SIZE, InstrumentNotFoundError, APIError
from logger import setup_logger


class PriceLoader:
    """
    Загрузчик цен для одного (ticker, timeframe).
    Используется оркестратором в цикле.
    """

    def __init__(
            self,
            ticker: str,
            timeframe: str,
            broker,  # TConnector instance
            db,  # DBManager instance

            # 🪵 Логирование
            logger=None,
            log_file: str = "price_loader.log",
            log_level: str = "INFO",
    ):
        self.ticker = ticker
        self.timeframe = timeframe
        self.broker = broker
        self.db = db
        self.logger = logger or setup_logger(f"PriceLoader.{ticker}.{timeframe}", log_file, log_level)

        # Кэш UID (чтобы не запрашивать каждый раз)
        self._uid: Optional[str] = None

        # Статистика
        self.stats = {
            "candles_loaded": 0,
            "candles_saved": 0,
            "last_load_time": None,
            "errors": []
        }

    async def _ensure_uid(self) -> str:
        """Гарантирует наличие UID: БД → кэш брокера → запрос к API."""
        if self._uid:
            return self._uid

        # Пробуем БД
        uid = self.db.get_uid_by_ticker(self.ticker)
        if uid:
            self._uid = uid
            self.logger.debug(f"UID из БД: {uid}")
            return uid

        # Пробуем кэш брокера
        uid = await self.broker.get_instrument_uid(self.ticker)
        if uid:
            self._uid = uid
            # Синхронизируем инструмент в БД
            inst_info = self.broker._instruments_cache.get(self.ticker, {})
            if inst_info:
                self.db.upsert_instruments_batch([inst_info])
            self.logger.info(f"UID получен от брокера: {uid}")
            return uid

        raise InstrumentNotFoundError(f"Не удалось получить UID для {self.ticker}")

    async def load_incremental(
            self,
            history_depth_days: Optional[int] = None,
            max_candles: int = MAX_CANDLES_IN_MEMORY
    ) -> Dict[str, Any]:
        """
        Инкрементальная загрузка свечей.

        Логика:
        1. Берём last_date из БД
        2. Загружаем от last_date - overlap до now
        3. Сохраняем батчами (чтобы не сожрать память на 2GB VPS)
        """
        self.logger.info(f"🔄 Загрузка инкремента: {self.ticker}/{self.timeframe}")

        try:
            # 1. UID
            uid = await self._ensure_uid()

            # 2. Последняя дата в БД
            last_date = self.db.get_last_candle_date(self.ticker, self.timeframe)

            # 3. Загрузка от брокера
            candles = await self.broker.load_historical_data(
                ticker=self.ticker,
                uid=uid,
                timeframe=self.timeframe,
                last_known_date=last_date,
                history_depth_days=history_depth_days
            )
            self.stats["candles_loaded"] = len(candles)

            if not candles:
                self.logger.info("✅ Нет новых свечей для загрузки")
                return {**self.stats, "success": True}

            # 4. Сохранение батчами (важно для памяти!)
            saved_total = 0
            for i in range(0, len(candles), BATCH_SAVE_SIZE):
                batch = candles[i:i + BATCH_SAVE_SIZE]
                saved = self.db.save_candles(batch, self.ticker, self.timeframe)
                saved_total += saved
                # Даём сборщику мусора передохнуть
                await asyncio.sleep(0.05)

            self.stats["candles_saved"] = saved_total
            self.stats["last_load_time"] = datetime.now()

            self.logger.info(
                f"✅ Загружено {self.stats['candles_loaded']}, "
                f"сохранено {saved_total} свечей"
            )
            return {**self.stats, "success": True}

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.stats["errors"].append(error_msg)
            self.logger.error(f"❌ Ошибка загрузки: {error_msg}", exc_info=True)
            return {**self.stats, "success": False, "error": error_msg}

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику загрузки."""
        return {
            "ticker": self.ticker,
            "timeframe": self.timeframe,
            **self.stats
        }

    async def calculate_and_save_metrics(
            self,
            candles: List[Dict[str, Any]],
            metric_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Рассчитывает и сохраняет метрики после загрузки свечей.
        Вызывай этот метод после save_candles().

        :return: dict с рассчитанными метриками
        """
        from metrics.engine import MetricsEngine

        if not candles:
            self.logger.debug("⚠️ Нет свечей для расчёта метрик")
            return {}

        try:
            engine = MetricsEngine(db=self.db, metric_names=metric_names)

            # Берём последние свечи для расчёта (сколько нужно для метрик)
            # Можно брать все, но обычно достаточно последних 100-200
            recent_candles = candles[-200:] if len(candles) > 200 else candles

            metrics = engine.calculate_for_candles(
                ticker=self.ticker,
                timeframe=self.timeframe,
                candles=recent_candles,
                candle_time=recent_candles[-1]['time'] if recent_candles else None
            )

            self.logger.info(f"✅ Метрики рассчитаны для {self.ticker}/{self.timeframe}: {list(metrics.keys())}")
            return metrics

        except ImportError as e:
            self.logger.warning(f"⚠️ MetricsEngine не доступен: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчёта метрик: {e}", exc_info=True)
            return {}