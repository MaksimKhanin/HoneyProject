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
    """RSI (Relative Strength Index) с периодом 14."""
    name = "rsi_14"
    description = "RSI(14) — индикатор перекупленности/перепроданности"
    
    @property
    def min_candles(self) -> int:
        return 15  # 14 для расчёта + 1 для сравнения

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        closes = df['close']
        
        # Векторизированный расчёт RSI через pandas
        delta = closes.diff()
        period = 14
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # Защита от деления на ноль
        rs = gain / loss.replace(0, float('inf'))
        rsi = 100 - (100 / (1 + rs))
        
        # Возвращаем последнее значение
        rsi_value = rsi.iloc[-1]
        if math.isnan(rsi_value) or math.isinf(rsi_value):
            return {}
        
        return {"rsi_14": round(rsi_value, 2)}


@register_metric
class ZScoreMetric(PandasMetric):
    """Z-Score цены за период."""
    name = "z_score_200"
    description = "Z-score цены за 200 свечей"
    
    @property
    def min_candles(self) -> int:
        return 100

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
        
        return {"z_score_200": round(z_score, 2)}


@register_metric
class PriceChangeMetric(PandasMetric):
    """Изменение цены за период в %."""
    name = "price_change_pct_3"
    description = "Изменение цены за последние 3 свечей в %"
    
    @property
    def min_candles(self) -> int:
        return 3

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        closes = df['close']
        
        if len(closes) < self.min_candles:
            return {}
        
        old_price = closes.iloc[-self.min_candles]
        new_price = closes.iloc[-1]
        
        if old_price == 0 or math.isnan(old_price) or math.isnan(new_price):
            return {}
        
        change_pct = (new_price - old_price) / old_price * 100
        
        return {"price_change_pct_5": round(change_pct, 2)}


@register_metric
class SkewKurtosisMetric(PandasMetric):
    """Асимметрия и эксцесс лог-доходностей на закрытиях (Close-to-Close)."""
    name = "skew_kurt_200"
    description = "Skewness и Excess Kurtosis по окну 200 свечей (на закрытиях)"
    
    @property
    def min_candles(self) -> int:
        return 100

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
            "skew_200": round(skew, 4),
            "kurt_excess_200": round(kurt, 4)
        }


@register_metric
class Pullback20Metric(PandasMetric):
    """Откат цены от локального максимума за окно."""
    name = "pullback_20"
    description = "Pullback % от max(close) за 20 свечей"
    
    @property
    def min_candles(self) -> int:
        return 20

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        closes = df['close'].iloc[-self.min_candles:]
        
        if len(closes) < self.min_candles:
            return {}
        
        max_close = closes.max()
        current_close = closes.iloc[-1]
        
        if max_close <= 0 or math.isnan(max_close) or math.isnan(current_close):
            return {}
        
        pullback = (max_close - current_close) / max_close
        return {"pullback_20": round(pullback, 4)}


@register_metric
class EMA50Metric(PandasMetric):
    """Экспоненциальная скользящая средняя (EMA) c периодом 50"""
    name = "ema_50"
    description = "EMA(50) цены закрытия"
    period = 50
    
    @property
    def min_candles(self) -> int:
        # Математически для adjust=False достаточно 1 свечи,
        # но первые ~span значений сильно смещены из-за отсутствия истории.
        # Для сходимости нужно Period*2, чтобы отдавать адекватное значение.
        return 100

    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        closes = df['close'].iloc[-self.min_candles:]
        
        if len(closes) < self.min_candles:
            return {}
        
        # Используем встроенную EMA pandas (соответствует adjust=False)
        ema = closes.ewm(span=self.period, adjust=False).mean().iloc[-1]
        
        if math.isnan(ema):
            return {}
        
        return {"ema_50": round(ema, 4)}


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
