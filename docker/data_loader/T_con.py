import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from t_tech.invest import AsyncClient, CandleInterval, GetCandlesResponse
from t_tech.invest.utils import quotation_to_decimal
from t_tech.invest.schemas import InstrumentStatus

from logger import setup_logger
from config_manager import get_config_manager


class T_connector:
    """
    Клиент для работы с Tinkoff Invest API.
    Использует ConfigManager для получения настроек.
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config_manager = get_config_manager(config_path)
        self.config = self.config_manager.get_config()

        self.logger = setup_logger(
            "TinkoffBroker",
            self.config['settings']['log_file'],
            self.config['settings']['log_level']
        )

        self.token = self.config['tinkoff']['token']
        self._instruments_cache = {}

        if not self.token or self.token == "YOUR_TOKEN_HERE":
            raise ValueError("Токен не указан в конфиге! Проверь config.yaml")

        self.logger.info("T_connector инициализирован успешно.")

    def reload_config(self):
        """Перезагрузка конфига (вызывается при изменении)."""
        self.config = self.config_manager.get_config()
        self.logger.info("Конфиг брокера обновлен")

    async def get_instrument_uid(self, ticker: str) -> Optional[str]:
        """Получение UID по тикеру с кэшированием."""
        # Проверяем кэш в памяти
        if hasattr(self, '_instruments_cache') and ticker in self._instruments_cache:
            cached = self._instruments_cache[ticker]
            self.logger.debug(f"UID для {ticker} взят из кэша: {cached['uid']}")
            return cached['uid']

        self.logger.debug(f"Кэш не найден для {ticker}, загружаем реестр...")

        # Загружаем всё и строим кэш
        instruments_list = await self._fetch_all_instruments_raw()
        self._instruments_cache = {inst['ticker']: inst for inst in instruments_list}

        # Ищем в кэше
        result = self._instruments_cache.get(ticker)
        if result:
            self.logger.info(f"Найден UID для {ticker}: {result['uid']} (type: {result['type']})")
            return result['uid']

        self.logger.warning(f"Тикер {ticker} не найден ни в одной категории.")
        return None

    async def _fetch_all_instruments_raw(self) -> List[Dict]:
        """Загрузка полного реестра инструментов."""
        self.logger.info("Загрузка полного реестра инструментов...")
        all_instruments = []

        async with AsyncClient(self.token) as client:
            # ✅ Обычные категории (вызываются без аргументов)
            categories = ["shares", "bonds", "etfs", "currencies", "futures"]

            for category in categories:
                try:
                    method = getattr(client.instruments, category)
                    response = await method()  # Без аргументов

                    for item in response.instruments:
                        inst_dict = {
                            "ticker": item.ticker,
                            "uid": item.uid,
                            "figi": item.figi,
                            "name": item.name,
                            "class_code": item.class_code,
                            "type": category,
                            "currency": item.currency,
                            "exchange": item.exchange,
                            "lot": item.lot,
                            "min_price_increment": quotation_to_decimal(item.min_price_increment),
                            "api_trade_available": getattr(item, 'api_trade_available_flag', False),
                            "updated_at": datetime.now()
                        }
                        all_instruments.append(inst_dict)

                    self.logger.debug(f"Категория {category}: загружено {len(response.instruments)} инструментов")

                except Exception as e:
                    self.logger.warning(f"Не удалось загрузить категорию {category}: {e}")
                    continue

            # ✅ ИНДИКАТИВЫ — отдельная обработка (требуют IndicativesRequest)
            try:
                self.logger.info("Загрузка индикативов (индексы, товары)...")
                from t_tech.invest.schemas import IndicativesRequest

                request = IndicativesRequest()
                response = await client.instruments.indicatives(request=request)

                for item in response.instruments:
                    inst_dict = {
                        "type": "indicative",
                        "ticker": item.ticker,
                        "name": item.name,
                        "uid": item.uid,
                        "figi": item.figi,
                        "currency": item.currency,
                        "updated_at": datetime.now()
                    }
                    all_instruments.append(inst_dict)

                self.logger.info(f"Индикативы: загружено {len(response.instruments)} инструментов")

            except Exception as e:
                self.logger.warning(f"Не удалось загрузить индикативы: {e}")

        self.logger.info(f"Всего загружено инструментов: {len(all_instruments)}")
        return all_instruments

    async def refresh_instruments_cache(self) -> Dict:
        """Принудительное обновление кэша инструментов."""
        self.logger.info("Принудительное обновление кэша инструментов...")
        instruments_list = await self._fetch_all_instruments_raw()
        self._instruments_cache = {inst['ticker']: inst for inst in instruments_list}
        self.logger.info(f"Кэш обновлен: {len(self._instruments_cache)} инструментов")
        return self._instruments_cache

    async def fetch_candles_chunk(
            self,
            uid: str,
            interval: CandleInterval,
            from_date: datetime,
            to_date: datetime
    ) -> List[Dict]:
        """Запрос одного куска свечей."""
        try:
            async with AsyncClient(self.token) as client:
                self.logger.debug(f"Запрос свечей: {uid} [{from_date} -> {to_date}]")

                response: GetCandlesResponse = await client.market_data.get_candles(
                    instrument_id=uid,
                    interval=interval,
                    from_=from_date,
                    to=to_date
                )

                candles_list = []
                for candle in response.candles:
                    candles_list.append({
                        "time": candle.time.replace(tzinfo=None),
                        "open": float(quotation_to_decimal(candle.open)),
                        "high": float(quotation_to_decimal(candle.high)),
                        "low": float(quotation_to_decimal(candle.low)),
                        "close": float(quotation_to_decimal(candle.close)),
                        "volume": candle.volume
                    })

                self.logger.debug(f"Получено {len(candles_list)} свечей.")
                return candles_list

        except Exception as e:
            self.logger.error(f"Ошибка загрузки свечей для {uid}: {e}", exc_info=True)
            raise

    def get_instruments_from_config(self) -> List[Dict[str, Any]]:
        """
        Получение информации по инструментам из конфига.
        Берет данные из кэша, а не делает новые API-запросы.
        Возвращает только включенные инструменты.
        """
        self.logger.info("Сбор информации по инструментам из конфига...")
        instruments_data = []

        # Убеждаемся, что кэш загружен
        if not hasattr(self, '_instruments_cache') or not self._instruments_cache:
            self.logger.warning(
                "Кэш инструментов пуст. Сначала вызовите get_instrument_uid() или refresh_instruments_cache()")
            return []

        # Получаем список тикеров из конфига через ConfigManager
        config_instruments = self.config_manager.get_instruments(enabled_only=True)

        for inst_config in config_instruments:
            ticker = inst_config['ticker']

            if ticker in self._instruments_cache:
                inst = self._instruments_cache[ticker]
                info = {
                    "ticker": inst['ticker'],
                    "uid": inst['uid'],
                    "name": inst['name'],
                    "type": inst['type'],
                    "currency": inst['currency'],
                    "exchange": inst['exchange'],
                    "updated_at": datetime.now()
                }
                instruments_data.append(info)
                self.logger.debug(f"Данные получены из кэша: {ticker} -> {inst['name']}")
            else:
                self.logger.warning(f"Инструмент {ticker} не найден в кэше.")

        self.logger.info(f"Найдено {len(instruments_data)} инструментов из конфига в кэше")
        return instruments_data

    async def load_historical_data(
            self,
            ticker: str,
            uid: str,
            timeframe: str = "1m",
            last_known_date: Optional[datetime] = None,
            history_depth_days: Optional[int] = None
    ) -> List[Dict]:
        """Загрузка истории с overlap window и приоритетом локальной глубины."""

        self.logger.info(
            f"Старт загрузки истории для {ticker} (UID: {uid}). Последняя известная дата: {last_known_date}")

        interval_map = {
            "1m": (CandleInterval.CANDLE_INTERVAL_1_MIN, 1, timedelta(minutes=30)),
            "5m": (CandleInterval.CANDLE_INTERVAL_5_MIN, 7, timedelta(hours=1)),
            "15m": (CandleInterval.CANDLE_INTERVAL_15_MIN, 28, timedelta(hours=3)),
            "1h": (CandleInterval.CANDLE_INTERVAL_HOUR, 60, timedelta(hours=12)),
            "1d": (CandleInterval.CANDLE_INTERVAL_DAY, 365, timedelta(days=3)),
        }

        if timeframe not in interval_map:
            raise ValueError(f"Неподдерживаемый таймфрейм: {timeframe}")

        interval, max_days_per_request, overlap_window = interval_map[timeframe]

        to_date = datetime.now()

        if last_known_date:
            # 🔥 Инкремент: используем overlap, игнорируем history_depth
            from_date = last_known_date - overlap_window
            self.logger.info(f"Режим инкремента: с {from_date} (overlap: {overlap_window})")
        else:
            # 🔥 Первая загрузка: приоритет — переданный history_depth_days
            if history_depth_days is not None:
                depth = history_depth_days
                source = "из конфига инструмента"
            else:
                depth = self.config['settings'].get('default_history_depth_days', 365)
                source = "глобальный дефолт"

            from_date = to_date - timedelta(days=depth)
            self.logger.info(f"Режим полной загрузки: с {from_date} (глубина {depth} дн., {source})")

        all_candles = []
        current_from = from_date

        while current_from < to_date:
            current_to = min(current_from + timedelta(days=max_days_per_request), to_date)

            try:
                chunk = await self.fetch_candles_chunk(uid, interval, current_from, current_to)
                all_candles.extend(chunk)
                self.logger.info(
                    f"Загружен кусок [{current_from} - {current_to}]: {len(chunk)} свечей. Всего: {len(all_candles)}")
            except Exception as e:
                self.logger.error(f"Критическая ошибка при загрузке куска. Прерывание. Ошибка: {e}")
                break

            current_from = current_to
            await asyncio.sleep(0.2)

        self.logger.info(f"Загрузка для {ticker} завершена. Всего получено: {len(all_candles)} свечей.")
        return all_candles