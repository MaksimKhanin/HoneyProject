#T_con.py


import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from t_tech.invest import AsyncClient, CandleInterval, GetCandlesResponse
from t_tech.invest.utils import quotation_to_decimal
from t_tech.invest.schemas import IndicativesRequest

from logger import setup_logger
from constants import (
    TIMEFRAMES,
    INSTRUMENT_CATEGORIES,
    INDICATIVES_CATEGORY,
    DEFAULT_LOG_FILE,
    DEFAULT_LOG_LEVEL,
    DEFAULT_TIMEOUT_SEC,
    DEFAULT_RETRIES,
    RETRY_DELAY_SEC,
    API_RATE_LIMIT_DELAY,
    DEFAULT_CACHE_TTL_SEC,
)

def _money_to_float(mv) -> float:
    """Конвертирует MoneyValue в float."""
    if mv is None:
        return 0.0
    return float(getattr(mv, 'units', 0)) + float(getattr(mv, 'nano', 0)) / 1e9

def _qty_to_float(q) -> float:
    """Конвертирует Quotation (количество) в float."""
    if q is None:
        return 0.0
    return float(getattr(q, 'units', 0)) + float(getattr(q, 'nano', 0)) / 1e9



class TConnector:
    """
    Клиент для работы с Tinkoff Invest API.

    Все настройки передаются явно в __init__ — никаких магических конфигов!
    Как хороший трейдер: знаешь свои параметры входа, стопа и тейка.
    """

    def __init__(
            self,
            # 🔑 Обязательные параметры
            token: str,

            # 🪵 Логирование
            log_file: str = DEFAULT_LOG_FILE,
            log_level: str = DEFAULT_LOG_LEVEL,

            # ⚙️ API настройки
            timeout_sec: int = DEFAULT_TIMEOUT_SEC,
            retries: int = DEFAULT_RETRIES,
            retry_delay_sec: float = RETRY_DELAY_SEC,
            rate_limit_delay: float = API_RATE_LIMIT_DELAY,

            # 📦 Кэширование
            cache_ttl_sec: int = DEFAULT_CACHE_TTL_SEC,

            # 📊 Загрузка истории (дефолты)
            default_history_depth_days: int = 365,
    ):
        # 🔐 Валидация токена (сразу фейлим, если что-то не так)
        if not token or token in ("YOUR_TOKEN_HERE", "xxx"):
            raise ValueError("❌ Токен не указан или невалидный! Передай реальный токен в конструктор.")

        self.token = token
        self.timeout_sec = timeout_sec
        self.retries = retries
        self.retry_delay_sec = retry_delay_sec
        self.rate_limit_delay = rate_limit_delay
        self.cache_ttl_sec = cache_ttl_sec
        self.default_history_depth_days = default_history_depth_days

        # 🪵 Логгер
        self.logger = setup_logger("TConnector", log_file, log_level)

        # 📦 Кэш инструментов (в памяти)
        self._account_id: Optional[str] = None
        self._instruments_cache: Dict[str, Dict] = {}
        self._cache_loaded_at: Optional[datetime] = None

        self.logger.info(f"✅ TConnector инициализирован. Готов сосать... то есть, работать с Tinkoff API.")

    # ===== Управление кэшем =====

    def _is_cache_valid(self) -> bool:
        """Проверяет, не истёк ли срок жизни кэша."""
        if not self._cache_loaded_at:
            return False
        age = (datetime.now() - self._cache_loaded_at).total_seconds()
        return age < self.cache_ttl_sec

    async def _fetch_all_instruments_raw(self) -> List[Dict]:
        """Загрузка полного реестра инструментов из API."""
        self.logger.info("📦 Загрузка реестра инструментов из Tinkoff API...")
        all_instruments = []

        async with AsyncClient(self.token) as client:
            # 📋 Обычные категории
            for category in INSTRUMENT_CATEGORIES:
                try:
                    method = getattr(client.instruments, category)
                    response = await method()

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
                            "min_price_increment": float(quotation_to_decimal(item.min_price_increment)),
                            "api_trade_available": getattr(item, 'api_trade_available_flag', False),
                            "updated_at": datetime.now()
                        }
                        all_instruments.append(inst_dict)

                    self.logger.debug(f"Категория {category}: {len(response.instruments)} инструментов")

                except Exception as e:
                    self.logger.warning(f"⚠️ Не удалось загрузить {category}: {e}")
                    continue

            # 📈 Индикативы (индексы, товары) — отдельная обработка
            try:
                self.logger.info("Загрузка индикативов...")
                request = IndicativesRequest()
                response = await client.instruments.indicatives(request=request)

                for item in response.instruments:
                    inst_dict = {
                        "type": INDICATIVES_CATEGORY,
                        "ticker": item.ticker,
                        "name": item.name,
                        "uid": item.uid,
                        "figi": item.figi,
                        "currency": item.currency,
                        "updated_at": datetime.now()
                    }
                    all_instruments.append(inst_dict)

                self.logger.info(f"Индикативы: {len(response.instruments)} инструментов")

            except Exception as e:
                self.logger.warning(f"⚠️ Не удалось загрузить индикативы: {e}")

        self.logger.info(f"✅ Всего загружено: {len(all_instruments)} инструментов")
        return all_instruments

    async def refresh_instruments_cache(self) -> Dict[str, Dict]:
        """Принудительное обновление кэша инструментов."""
        self.logger.info("🔄 Принудительное обновление кэша...")
        instruments_list = await self._fetch_all_instruments_raw()
        self._instruments_cache = {inst['ticker']: inst for inst in instruments_list}
        self._cache_loaded_at = datetime.now()
        self.logger.info(f"✅ Кэш обновлен: {len(self._instruments_cache)} инструментов")
        return self._instruments_cache

    async def get_instrument_uid(self, ticker: str) -> Optional[str]:
        """Получение UID по тикеру с кэшированием."""
        # Проверяем кэш
        if ticker in self._instruments_cache:
            cached = self._instruments_cache[ticker]
            # Проверяем актуальность кэша
            if self._is_cache_valid():
                self.logger.debug(f"📦 UID для {ticker} из кэша: {cached['uid']}")
                return cached['uid']
            else:
                self.logger.debug(f"⏰ Кэш устарел, обновляем для {ticker}")

        # Кэш пуст или устарел — загружаем заново
        await self.refresh_instruments_cache()

        result = self._instruments_cache.get(ticker)
        if result:
            self.logger.info(f"✅ Найден UID для {ticker}: {result['uid']}")
            return result['uid']

        self.logger.warning(f"❌ Тикер {ticker} не найден в реестре Tinkoff")
        return None

    # ===== Свечи =====

    async def fetch_candles_chunk(
            self,
            uid: str,
            interval: CandleInterval,
            from_date: datetime,
            to_date: datetime
    ) -> List[Dict]:
        """Запрос одного куска свечей с ретраями."""

        # 🔄 Простая логика ретраев (можно вынести в декоратор)
        for attempt in range(self.retries):
            try:
                async with AsyncClient(self.token) as client:
                    self.logger.debug(f"🕯️ Запрос свечей: {uid} [{from_date} -> {to_date}]")

                    response: GetCandlesResponse = await client.market_data.get_candles(
                        instrument_id=uid,
                        interval=interval,
                        from_=from_date,
                        to=to_date
                    )

                    candles_list = []
                    for candle in response.candles:
                        candles_list.append({
                            "time": candle.time.replace(tzinfo=None),  # Убираем tzinfo для единообразия с БД
                            "open": float(quotation_to_decimal(candle.open)),
                            "high": float(quotation_to_decimal(candle.high)),
                            "low": float(quotation_to_decimal(candle.low)),
                            "close": float(quotation_to_decimal(candle.close)),
                            "volume": candle.volume
                        })

                    self.logger.debug(f"✅ Получено {len(candles_list)} свечей")
                    return candles_list

            except Exception as e:
                if attempt < self.retries - 1:
                    self.logger.warning(f"⚠️ Попытка {attempt + 1} не удалась: {e}. Ждём {self.retry_delay_sec}с...")
                    await asyncio.sleep(self.retry_delay_sec)
                else:
                    self.logger.error(f"❌ Все {self.retries} попыток исчерпаны. Ошибка: {e}", exc_info=True)
                    raise

    async def load_historical_data(
            self,
            ticker: str,
            uid: str,
            timeframe: str = "1m",
            last_known_date: Optional[datetime] = None,
            history_depth_days: Optional[int] = None
    ) -> List[Dict]:
        """Загрузка истории с overlap window и умной логикой глубины."""

        # 🔍 Валидация таймфрейма
        if timeframe not in TIMEFRAMES:
            raise ValueError(f"❌ Неподдерживаемый таймфрейм: {timeframe}. Доступные: {list(TIMEFRAMES.keys())}")

        tf_config = TIMEFRAMES[timeframe]
        interval = CandleInterval(tf_config["interval_code"])
        max_days = tf_config["max_days_per_request"]
        overlap = tf_config["overlap_window"]

        to_date = datetime.now()

        # 🎯 Логика выбора диапазона
        if last_known_date:
            # 🔁 Инкрементальная загрузка: берём с небольшим "нахлёстом"
            from_date = last_known_date - overlap
            self.logger.info(f"🔁 Инкремент: [{from_date} -> {to_date}] (overlap: {overlap})")
        else:
            # 🆕 Первая загрузка: используем глубину
            depth = history_depth_days if history_depth_days is not None else self.default_history_depth_days
            from_date = to_date - timedelta(days=depth)
            source = "параметр" if history_depth_days is not None else "дефолт"
            self.logger.info(f"🆕 Полная загрузка: глубина {depth} дн. ({source})")

        all_candles = []
        current_from = from_date

        # 🔄 Цикл загрузки кусками (чтобы не превысить лимиты API)
        while current_from < to_date:
            current_to = min(current_from + timedelta(days=max_days), to_date)

            try:
                chunk = await self.fetch_candles_chunk(uid, interval, current_from, current_to)
                all_candles.extend(chunk)
                self.logger.info(
                    f"📥 Кусок [{current_from.strftime('%m-%d %H:%M')} - {current_to.strftime('%m-%d %H:%M')}]: "
                    f"{len(chunk)} свечей. Всего: {len(all_candles)}"
                )
            except Exception as e:
                self.logger.error(f"💥 Критическая ошибка при загрузке. Прерывание. Ошибка: {e}")
                break

            current_from = current_to
            # 🐌 Задержка, чтобы не словить rate limit от Tinkoff
            await asyncio.sleep(self.rate_limit_delay)

        self.logger.info(f"✅ Загрузка для {ticker} завершена. Всего: {len(all_candles)} свечей")
        return all_candles

    # ===== Работа с инструментами извне =====

    def get_instruments_from_list(
            self,
            tickers: List[str],
            require_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получение данных по списку тикеров из кэша.

        Вместо чтения из конфига — принимаем список тикеров явно.
        Гибко, как стоп-лосс под волатильность.
        """
        if require_cache and (not self._instruments_cache or not self._is_cache_valid()):
            self.logger.warning("⚠️ Кэш пуст или устарел. Вызовите refresh_instruments_cache() сначала.")
            return []

        instruments_data = []
        for ticker in tickers:
            if ticker in self._instruments_cache:
                inst = self._instruments_cache[ticker]
                instruments_data.append({
                    "ticker": inst['ticker'],
                    "uid": inst['uid'],
                    "name": inst['name'],
                    "type": inst['type'],
                    "currency": inst['currency'],
                    "exchange": inst['exchange'],
                    "updated_at": datetime.now()
                })
                self.logger.debug(f"📦 {ticker} -> {inst['name']}")
            else:
                self.logger.warning(f"❌ {ticker} не найден в кэше")

        self.logger.info(f"✅ Найдено {len(instruments_data)} из {len(tickers)} инструментов")
        return instruments_data

    async def get_positions(self, account_id: str = None) -> List[Dict[str, Any]]:
        """
        Получает все открытые позиции из Tinkoff API.
        """
        if account_id is None:
            account_id = await self.get_account_id()

        positions = []

        try:
            async with AsyncClient(self.token) as client:
                # ✅ ИСПРАВЛЕНО: response.positions, а не total_positions
                response = await client.operations.get_portfolio(account_id=account_id)

                for pos in response.positions:
                    try:
                        avg_price = _money_to_float(pos.average_position_price)
                        current_price = _money_to_float(pos.current_price) if pos.current_price else None

                        qty = _qty_to_float(pos.quantity)
                        qty_lots = _qty_to_float(pos.quantity_lots) if pos.quantity_lots else qty

                        # Считаем стоимости
                        entry_value = avg_price * qty
                        current_value = current_price * qty if current_price else None

                        unrealized_pnl = current_value - entry_value if current_value else None
                        pnl_percent = (unrealized_pnl / entry_value * 100) if entry_value != 0 else None

                        # Тикер может отсутствовать у валют/облигаций → fallback на UID
                        ticker = getattr(pos, 'ticker', '') or pos.instrument_uid[:8]

                        pos_dict = {
                            "account_id": account_id,
                            "instrument_uid": pos.instrument_uid,
                            "figi": pos.figi,
                            "ticker": ticker.upper(),
                            "instrument_type": pos.instrument_type,
                            "position_type": "Long" if qty > 0 else "Short",
                            "quantity": int(qty),
                            "quantity_lots": float(qty_lots),
                            "average_position_price": round(avg_price, 6),
                            "current_price": round(current_price, 6) if current_price else None,
                            "entry_value": round(entry_value, 2),
                            "current_value": round(current_value, 2) if current_value else None,
                            "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl else None,
                            "unrealized_pnl_percent": round(pnl_percent, 2) if pnl_percent else None,
                            "currency": (getattr(pos.average_position_price, 'currency', 'RUB') or 'RUB').upper(),
                            "blocked": bool(getattr(pos, 'blocked', False)),
                            "updated_at": datetime.now()
                        }
                        positions.append(pos_dict)

                    except Exception as e:
                        self.logger.warning(f"⚠️ Не удалось обработать позицию {pos.instrument_uid}: {e}")
                        continue

                self.logger.info(f"✅ Получено {len(positions)} позиций для аккаунта {account_id}")
                return positions

        except Exception as e:
            self.logger.error(f"❌ Ошибка получения позиций: {e}", exc_info=True)
            raise

    async def get_position_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Получает позицию по тикеру (удобно для фильтрации)."""
        positions = await self.get_positions()
        for pos in positions:
            if pos.get("ticker") == ticker.upper():
                return pos
        return None

    async def get_portfolio_summary(self, account_id: str = None) -> Dict[str, Any]:
        """Получает сводку по портфелю."""
        if account_id is None:
            account_id = await self.get_account_id()

        try:
            async with AsyncClient(self.token) as client:
                response = await client.operations.get_portfolio(account_id=account_id)

                # ✅ Берём базовую валюту прямо из ответа API
                base_currency = getattr(response.total_amount_portfolio, 'currency', 'RUB').upper()
                total_value = _money_to_float(response.total_amount_portfolio)

                positions = await self.get_positions(account_id=account_id)
                total_pnl = sum(p["unrealized_pnl"] or 0 for p in positions)

                summary = {
                    "account_id": account_id,
                    "total_value": round(total_value, 2),
                    "total_pnl": round(total_pnl, 2),
                    "total_pnl_percent": round(total_pnl / total_value * 100, 2) if total_value != 0 else None,
                    "base_currency": base_currency,  # ← НОВОЕ ПОЛЕ
                    "positions_count": len(positions),
                    "long_positions": sum(1 for p in positions if p["position_type"] == "Long"),
                    "short_positions": sum(1 for p in positions if p["position_type"] == "Short"),
                    "currencies": sorted(list(set(p["currency"] for p in positions if p["currency"]))),
                    "updated_at": datetime.now()
                }
                return summary
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения сводки портфеля: {e}", exc_info=True)
            raise

    async def get_positions_with_config_filter(self, db, account_id: str = None) -> List[Dict[str, Any]]:
        """Получает позиции брокера, фильтрует только те, что есть в instrument_config."""

        # 1. Получаем все позиции от брокера
        try:
            all_positions = await self.get_positions(account_id=account_id)
            self.logger.info(f"🔍 Broker positions: {len(all_positions)} found")

            # 🔥 ДЕБАГ: логируем тикеры из брокера
            broker_tickers = [p.get("ticker", "").upper() for p in all_positions if p.get("ticker")]
            self.logger.debug(f"🔍 Broker tickers: {broker_tickers}")

        except Exception as e:
            self.logger.error(f"❌ Error getting positions: {e}", exc_info=True)
            return []

        if not all_positions:
            return []

        # 2. Получаем отслеживаемые тикеры из БД (приводим к верхнему регистру!)
        configs = db.get_all_instrument_configs()
        tracked = {
            cfg["ticker"].upper(): cfg  # ← Ключ в верхнем регистре для надёжного сравнения
            for cfg in configs
            if cfg.get("ticker")
        }

        self.logger.info(f"🔍 Tracked tickers from DB: {list(tracked.keys())}")

        # 3. Фильтруем + обогащаем
        filtered = []
        for pos in all_positions:
            pos_ticker = (pos.get("ticker") or "").upper()

            if pos_ticker in tracked:
                cfg = tracked[pos_ticker]
                # Обогащаем данными из конфига
                pos["strategy_name"] = cfg.get("strategy_name", "none")
                pos["timeframe"] = cfg.get("timeframe", "1d")
                pos["strategy_window"] = cfg.get("strategy_window")
                filtered.append(pos)
                self.logger.debug(f"✅ Matched: {pos_ticker} → strategy={cfg.get('strategy_name')}")
            else:
                self.logger.debug(f"⚠️ No match for {pos_ticker} (tracked: {list(tracked.keys())})")

        self.logger.info(f"🔍 Filtered positions: {len(filtered)} of {len(all_positions)}")
        return filtered

    async def get_account_id(self, account_type: str = None) -> str:
        """Получает ID основного торгового счёта."""
        if self._account_id:
            return self._account_id

        try:
            async with AsyncClient(self.token) as client:
                response = await client.users.get_accounts()
                if not response.accounts:
                    raise ValueError("❌ Не найдено ни одного аккаунта для этого токена")

                accounts = list(response.accounts)
                if account_type:
                    accounts = [a for a in accounts if a.account_type == account_type]

                # 🔍 Ищем открытый счёт. В SDK статус 2 = ACCOUNT_STATUS_OPEN
                for acc in accounts:
                    # Поддержка и int (2), и строки ("ACCOUNT_STATUS_OPEN")
                    is_open = str(acc.status).upper() in ("2", "ACCOUNT_STATUS_OPEN", "OPEN")
                    if is_open:
                        self._account_id = acc.id
                        self.logger.info(f"✅ Выбран аккаунт: {acc.id}")
                        return acc.id

                # Фоллбэк: берём первый, если открытых не нашли
                fallback = accounts[0]
                self._account_id = fallback.id
                self.logger.warning(
                    f"⚠️ Открытых счетов не найдено, используем: {fallback.id} (статус: {fallback.status})")
                return fallback.id

        except Exception as e:
            self.logger.error(f"❌ Ошибка получения аккаунта: {e}", exc_info=True)
            raise

    async def get_all_accounts(self) -> List[Dict[str, Any]]:
        """
        Получает список всех аккаунтов (для отладки/выбора).

        Возвращает:
        [
            {
                "id": "1234567890",
                "name": "Брокерский счёт",
                "status": "ACCOUNT_STATUS_OPEN",
                "account_type": "Tinkoff",
                "currency": "RUB",
                "opened_date": datetime(...),
            },
            ...
        ]
        """
        accounts = []

        try:
            async with AsyncClient(self.token) as client:
                response = await client.users.get_accounts()

                for acc in response.accounts:
                    accounts.append({
                        "id": acc.id,
                        "name": acc.name,
                        "status": acc.status,
                        #"account_type": acc.account_type,
                        #"currency": acc.currency,
                        "opened_date": acc.opened_date,
                    })

                self.logger.info(f"✅ Получено {len(accounts)} аккаунтов")
                return accounts

        except Exception as e:
            self.logger.error(f"❌ Ошибка получения списка аккаунтов: {e}", exc_info=True)
            raise

    # ===== Утилиты =====

    async def close(self):
        """Очистка ресурсов (если нужно)."""
        self.logger.info("🔌 TConnector закрыт")
        self._instruments_cache.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False