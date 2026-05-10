# core/metrics/base.py
"""
Базовые классы для метрик.
Два шаблона: SQL (расчёт в БД) и Python/Pandas (расчёт в коде).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

logger = logging.getLogger(__name__)


class BaseMetric(ABC):
    """
    Абстрактный базовый класс для всех метрик.

    Каждая метрика должна реализовать:
    - name: уникальный идентификатор
    - description: человекочитаемое описание
    - calculate(): логика расчёта
    """

    name: str
    description: str
    depends_on: List[str] = []  # Зависимости от других метрик (опционально)

    @abstractmethod
    def calculate(
            self,
            ticker: str,
            timeframe: str,
            candles: List[Dict[str, Any]],
            db=None,  # DBManager instance (опционально)
            **kwargs
    ) -> Dict[str, Any]:
        """
        Рассчитывает метрику.

        :param ticker: тикер инструмента
        :param timeframe: таймфрейм ("1m", "1h", etc.)
        :param candles: список свечей [{'time': ..., 'open': ..., ...}, ...]
        :param db: экземпляр DBManager (для SQL-метрик)
        :return: dict с результатами {"metric_name": value, ...}
        """
        pass

    def validate_input(self, candles: List[Dict]) -> bool:
        """Проверяет, достаточно ли данных для расчёта."""
        return len(candles) >= self.min_candles

    @property
    def min_candles(self) -> int:
        """
        Минимальное количество свечей для расчёта.
        Переопредели в наследнике, если нужно другое значение.
        """
        return getattr(self, '_min_candles', 10)  # дефолт 10

    @min_candles.setter
    def min_candles(self, value: int):
        """Позволяет задать min_candles динамически."""
        self._min_candles = value


# ===== ШАБЛОН 1: Метрика на Pandas (рекомендуемый) =====

class PandasMetric(BaseMetric):
    """
    Шаблон для метрик, рассчитываемых через pandas.
    
    Преимущества перед pure Python:
    - Векторизированные операции (быстрее в 10-100 раз)
    - Совместимость с backtesting.py (там тоже pandas)
    - Меньше багов при переходе между средой тестирования и production
    
    Параметризация:
    - period: период расчёта (например, 14 для RSI)
    - window: окно для скользящих расчётов
    
    Пример использования:
    ```
    # Создание метрики с кастомными параметрами
    rsi_metric = RSIMetric(period=14)
    rsi_metric_long = RSIMetric(period=21)
    
    class RSIMetric(PandasMetric):
        name = "rsi"
        description = "RSI — индикатор перекупленности/перепроданности"
        default_period = 14

        def calculate_pandas(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
            closes = df['close']
            delta = closes.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return {f"rsi_{self.period}": round(rsi.iloc[-1], 2)}
    ```
    """
    
    # Параметры по умолчанию (переопределяются в __init__)
    default_period: int = 14
    default_window: int = 20

    def __init__(self, period: Optional[int] = None, window: Optional[int] = None):
        """
        Инициализация метрики с параметрами.
        
        :param period: период расчёта (если не указан, используется default_period)
        :param window: окно для скользящих расчётов (если не указан, используется default_window)
        """
        self.period = period if period is not None else self.default_period
        self.window = window if window is not None else self.default_window
        
        # Динамическое формирование имени метрики, если оно не содержит параметров
        if hasattr(self, 'name') and not hasattr(self, '_name_fixed'):
            # Если имя содержит плейсхолдер, заменяем его
            if '{period}' in self.name:
                self.name = self.name.format(period=self.period)
            if '{window}' in self.name:
                self.name = self.name.format(window=self.window)

    @abstractmethod
    def calculate_pandas(
            self,
            df: 'pd.DataFrame',
            **kwargs
    ) -> Dict[str, Any]:
        """Реализуй расчёт здесь. Получаешь DataFrame со свечами."""
        pass

    def calculate(
            self,
            ticker: str,
            timeframe: str,
            candles: List[Dict[str, Any]],
            db=None,
            **kwargs
    ) -> Dict[str, Any]:
        # Валидация входных данных
        if not self.validate_input(candles):
            logger.debug(f"⚠️ {self.name}: недостаточно данных ({len(candles)} < {self.min_candles})")
            return {}

        if not PANDAS_AVAILABLE:
            logger.error(f"❌ {self.name}: требуется pandas, но он не установлен")
            return {}

        try:
            # Конвертируем свечи в DataFrame
            df = pd.DataFrame(candles)
            
            # Проверяем наличие необходимых колонок
            required_cols = {'open', 'high', 'low', 'close', 'volume'}
            missing_cols = required_cols - set(df.columns)
            if missing_cols:
                logger.error(f"❌ {self.name}: отсутствуют колонки {missing_cols}")
                return {}
            
            result = self.calculate_pandas(df, ticker=ticker, timeframe=timeframe, **kwargs)
            logger.debug(f"✅ {self.name} для {ticker}/{timeframe}: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Ошибка в {self.name} ({ticker}/{timeframe}): {e}", exc_info=True)
            return {}


# ===== ШАБЛОН 2: Метрика через SQL =====

class SQLMetric(BaseMetric):
    """
    Шаблон для метрик, рассчитываемых через SQL-запрос к БД.

    Пример использования:
    ```
    class VolumeAvgMetric(SQLMetric):
        name = "volume_avg_20"
        description = "Средний объём за 20 свечей"
        sql_query = \"\"\"
            SELECT AVG(volume) as volume_avg
            FROM candles
            WHERE ticker = %s AND timeframe = %s
            ORDER BY time DESC LIMIT 20
        \"\"\"

        def post_process(self, row: tuple) -> Dict[str, Any]:
            return {"volume_avg": float(row[0]) if row[0] else None}
    ```
    """

    sql_query: str  # Параметризованный SQL-запрос (%s для ticker, timeframe)

    @abstractmethod
    def post_process(self, row: tuple) -> Dict[str, Any]:
        """Преобразует результат SQL-запроса (кортеж) в dict метрик."""
        pass

    def calculate(
            self,
            ticker: str,
            timeframe: str,
            candles: List[Dict[str, Any]],
            db,  # DBManager обязателен для SQL-метрик
            **kwargs
    ) -> Dict[str, Any]:
        if not db:
            logger.error(f"❌ {self.name}: требуется DBManager для SQL-запроса")
            return {}

        try:
            conn = db._get_connection()
            cur = conn.cursor()
            cur.execute(self.sql_query, (ticker, timeframe))
            row = cur.fetchone()
            cur.close()
            db._release_connection(conn)

            if row:
                result = self.post_process(row)
                logger.debug(f"✅ {self.name} для {ticker}/{timeframe}: {result}")
                return result
            else:
                logger.debug(f"⚠️ {self.name}: нет данных в БД для {ticker}/{timeframe}")
                return {}

        except Exception as e:
            logger.error(f"❌ Ошибка в {self.name} ({ticker}/{timeframe}): {e}", exc_info=True)
            return {}


# ===== ШАБЛОН 3: Legacy Pure Python (для обратной совместимости) =====

class PythonMetric(BaseMetric):
    """
    Устаревший шаблон для метрик на чистом Python.
    Используется только для обратной совместимости.
    Новые метрики пишите на PandasMetric.
    """

    @abstractmethod
    def calculate_python(
            self,
            candles: List[Dict[str, Any]],
            **kwargs
    ) -> Dict[str, Any]:
        """Реализуй расчёт здесь. Получаешь только свечи, без БД."""
        pass

    def calculate(
            self,
            ticker: str,
            timeframe: str,
            candles: List[Dict[str, Any]],
            db=None,
            **kwargs
    ) -> Dict[str, Any]:
        # Валидация входных данных
        if not self.validate_input(candles):
            logger.debug(f"⚠️ {self.name}: недостаточно данных ({len(candles)} < {self.min_candles})")
            return {}

        try:
            result = self.calculate_python(candles, ticker=ticker, timeframe=timeframe, **kwargs)
            logger.debug(f"✅ {self.name} для {ticker}/{timeframe}: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Ошибка в {self.name} ({ticker}/{timeframe}): {e}", exc_info=True)
            return {}