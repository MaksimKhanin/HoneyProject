# core/metrics/builtins/python_metrics.py
"""
Встроенные метрики, рассчитываемые на pandas.
Все метрики переписаны с pure Python на pandas для совместимости с backtesting.py
"""

from typing import Dict, Any
import math
from ..base import PandasMetric
from ..registry import register_metric


@register_metric
class RSIMetric(PandasMetric):
    """RSI (Relative Strength Index) с настраиваемым периодом."""
    name = "rsi_{period}"
    description = "RSI — индикатор перекупленности/перепроданности"
    default_period = 14

    @property
    def min_candles(self) -> int:
        return self.period + 1  # period для расчёта + 1 для сравнения

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        closes = df['close']

        # Векторизированный расчёт RSI через pandas
        delta = closes.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()

        # Защита от деления на ноль
        rs = gain / loss.replace(0, float('inf'))
        rsi = 100 - (100 / (1 + rs))

        # Возвращаем последнее значение
        rsi_value = rsi.iloc[-1]
        if math.isnan(rsi_value) or math.isinf(rsi_value):
            return {}

        return {f"rsi_{self.period}": round(rsi_value, 2)}


@register_metric
class ZScoreMetric(PandasMetric):
    """Z-Score цены за настраиваемый период."""
    name = "z_score_{period}"
    description = "Z-score цены"
    default_period = 200

    @property
    def min_candles(self) -> int:
        return max(100, self.period // 2)  # Минимум половина периода

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        # Логарифмические доходности на закрытиях
        closes = df['close'].iloc[-self.min_candles:]

        # Защита от невалидных данных
        valid_closes = closes[(closes > 0) & (closes.notna())]
        if len(valid_closes) < 2:
            return {}

        log_rets = valid_closes.pct_change().dropna()
        log_rets = log_rets.apply(lambda x: math.log(1 + x) if abs(x) < 1 else None).dropna()

        if len(log_rets) < 2:
            return {}

        mean = log_rets.mean()
        std = log_rets.std(ddof=0)  # population std

        if std < 1e-12:
            return {}

        z_score = (log_rets.iloc[-1] - mean) / std

        return {f"z_score_{self.period}": round(z_score, 2)}


@register_metric
class PriceChangeMetric(PandasMetric):
    """Изменение цены за настраиваемый период в %."""
    name = "price_change_pct_{period}"
    description = "Изменение цены в %"
    default_period = 3

    @property
    def min_candles(self) -> int:
        return self.period

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        closes = df['close']

        if len(closes) < self.min_candles:
            return {}

        old_price = closes.iloc[-self.period]
        new_price = closes.iloc[-1]

        if old_price == 0 or math.isnan(old_price) or math.isnan(new_price):
            return {}

        change_pct = (new_price - old_price) / old_price * 100

        return {f"price_change_pct_{self.period}": round(change_pct, 2)}


@register_metric
class SkewKurtosisMetric(PandasMetric):
    """Асимметрия и эксцесс лог-доходностей на закрытиях (Close-to-Close)."""
    name = "skew_kurt_{period}"
    description = "Skewness и Excess Kurtosis"
    default_period = 200

    @property
    def min_candles(self) -> int:
        return max(100, self.period // 2)

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        # Логарифмические доходности на закрытиях
        closes = df['close']

        # Фильтрация невалидных данных
        valid_mask = (closes > 0) & (closes.notna())
        valid_closes = closes[valid_mask]

        if len(valid_closes) < 2:
            return {}

        # Лог-доходности
        log_rets = valid_closes.pct_change().dropna()
        log_rets = log_rets.apply(lambda x: math.log(1 + x) if abs(x) < 1 else None).dropna()

        window = self.min_candles - 1
        if len(log_rets) < window:
            return {}

        recent = log_rets.iloc[-window:]

        # Центральные моменты через pandas
        n = len(recent)
        mean = recent.mean()
        m2 = ((recent - mean) ** 2).mean()

        if m2 < 1e-12:
            return {}

        m3 = ((recent - mean) ** 3).mean()
        m4 = ((recent - mean) ** 4).mean()

        # Skew и Excess Kurtosis (Фишер)
        skew = m3 / (m2 ** 1.5)
        kurt = (m4 / (m2 ** 2)) - 3.0

        return {
            f"skew_{self.period}": round(skew, 4),
            f"kurt_excess_{self.period}": round(kurt, 4)
        }


@register_metric
class PullbackMetric(PandasMetric):
    """Откат цены от локального максимума за окно."""
    name = "pullback_{window}"
    description = "Pullback % от max(close)"
    default_window = 20

    @property
    def min_candles(self) -> int:
        return self.window

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        closes = df['close'].iloc[-self.window:]

        if len(closes) < self.min_candles:
            return {}

        max_close = closes.max()
        current_close = closes.iloc[-1]

        if max_close <= 0 or math.isnan(max_close) or math.isnan(current_close):
            return {}

        pullback = (max_close - current_close) / max_close
        return {f"pullback_{self.window}": round(pullback, 4)}


@register_metric
class EMAMetric(PandasMetric):
    """Экспоненциальная скользящая средняя (EMA) с настраиваемым периодом."""
    name = "ema_{period}"
    description = "EMA цены закрытия"
    default_period = 50

    @property
    def min_candles(self) -> int:
        # Математически для adjust=False достаточно 1 свечи,
        # но первые ~span значений сильно смещены из-за отсутствия истории.
        # Для сходимости нужно Period*2, чтобы отдавать адекватное значение.
        return self.period * 2

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        closes = df['close'].iloc[-self.min_candles:]

        if len(closes) < self.min_candles:
            return {}

        # Используем встроенную EMA pandas (соответствует adjust=False)
        ema = closes.ewm(span=self.period, adjust=False).mean().iloc[-1]

        if math.isnan(ema):
            return {}

        return {f"ema_{self.period}": round(ema, 4)}


@register_metric
class ClosePrice(PandasMetric):
    """Цена закрытия последней свечи."""
    name = "close_price"
    description = "Just a close price"

    @property
    def min_candles(self) -> int:
        return 1

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        if len(df) < self.min_candles:
            return {}

        close_price = df['close'].iloc[-1]

        if math.isnan(close_price):
            return {}

        return {"close_price": close_price}


@register_metric
class VolumeRatioMetric(PandasMetric):
    """Отношение текущего объёма к среднему объёму за период."""
    name = "vol_ratio_{period}"
    description = "Volume Ratio - отношение текущего объёма к среднему за период"
    default_period = 20

    @property
    def min_candles(self) -> int:
        return self.period + 1

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        volumes = df['volume'].iloc[-(self.period + 1):]

        if len(volumes) < self.min_candles:
            return {}

        # Средний объём за период (без последней свечи)
        avg_volume = volumes.iloc[:-1].mean()
        current_volume = volumes.iloc[-1]

        if avg_volume <= 0 or math.isnan(avg_volume) or math.isnan(current_volume):
            return {}

        vol_ratio = current_volume / avg_volume

        return {f"vol_ratio_{self.period}": round(vol_ratio, 4)}


@register_metric
class MovMinMetric(PandasMetric):
    """Минимальное значение Low за период."""
    name = "mov_min_{period}"
    description = "Moving Minimum - минимальное значение Low за период"
    default_period = 20

    @property
    def min_candles(self) -> int:
        return self.period

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        lows = df['low'].iloc[-self.period:]

        if len(lows) < self.min_candles:
            return {}

        mov_min = lows.min()

        if math.isnan(mov_min):
            return {}

        return {f"mov_min_{self.period}": round(mov_min, 4)}


@register_metric
class MovMaxMetric(PandasMetric):
    """Максимальное значение High за период."""
    name = "mov_max_{period}"
    description = "Moving Maximum - максимальное значение High за период"
    default_period = 20

    @property
    def min_candles(self) -> int:
        return self.period

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        highs = df['high'].iloc[-self.period:]

        if len(highs) < self.min_candles:
            return {}

        mov_max = highs.max()

        if math.isnan(mov_max):
            return {}

        return {f"mov_max_{self.period}": round(mov_max, 4)}