# core/metrics/builtins/python_metrics.py
"""
Встроенные метрики, рассчитываемые на Python.
"""

from typing import Dict, Any, List
import math
from ..base import PythonMetric
from ..registry import register_metric


@register_metric
class RSIMetric(PythonMetric):
    """RSI (Relative Strength Index) с периодом 14."""
    name = "rsi_14"
    description = "RSI(14) — индикатор перекупленности/перепроданности"
    min_candles = 15  # Нужно минимум 15 свечей для RSI(14)

    @property
    def min_candles(self) -> int:
        return 15  # 14 для расчёта + 1 для сравнения

    def calculate_python(self, candles: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        closes = [c['close'] for c in candles]

        # Простой расчёт RSI
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        period = 14

        if len(deltas) < period:
            return {}

        recent = deltas[-period:]
        gains = [d if d > 0 else 0 for d in recent]
        losses = [-d if d < 0 else 0 for d in recent]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        return {"rsi_14": round(rsi, 2)}


@register_metric
class ZScoreMetric(PythonMetric):
    """Z-Score цены за период."""
    name = "z_score_200"
    description = "Z-score цены за 200 свечей"
    min_candles = 100

    @property
    def min_candles(self) -> int:
        return 100

    def calculate_python(self, candles: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        closes = [c['close'] for c in candles[-self.min_candles:]]

        if len(closes) < self.min_candles:
            return {}

        # 1. Логарифмические доходности на закрытиях
        log_rets = []
        for i in range(1, len(candles)):
            prev_close = candles[i - 1]['close']
            curr_close = candles[i]['close']

            # Защита от деления на ноль и невалидных данных
            if prev_close is None or curr_close is None or prev_close <= 0 or curr_close <= 0:
                continue

            log_rets.append(math.log(curr_close / prev_close))

        closes = log_rets

        mean = sum(closes) / len(closes)
        variance = sum((x - mean) ** 2 for x in closes) / len(closes)
        std = math.sqrt(variance)

        z_score = (closes[-1] - mean) / std

        return {"z_score_200": round(z_score, 2)}


@register_metric
class PriceChangeMetric(PythonMetric):
    """Изменение цены за период в %."""
    name = "price_change_pct_3"
    description = "Изменение цены за последние 3 свечей в %"
    min_candles = 3

    def calculate_python(self, candles: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        if len(candles) < self.min_candles:
            return {}

        old_price = candles[-self.min_candles]['close']
        new_price = candles[-1]['close']

        if old_price == 0:
            return {}

        change_pct = (new_price - old_price) / old_price * 100

        return {"price_change_pct_5": round(change_pct, 2)}




@register_metric
class SkewKurtosisMetric(PythonMetric):
    """Асимметрия и эксцесс лог-доходностей на закрытиях (Close-to-Close)."""
    name = "skew_kurt_200"
    description = "Skewness и Excess Kurtosis по окну 200 свечей (на закрытиях)"
    min_candles = 100

    @property
    def min_candles(self) -> int:
        return 100

    def calculate_python(self, candles: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        if len(candles) < self.min_candles:
            return {}

        # 1. Логарифмические доходности на закрытиях
        log_rets = []
        for i in range(1, len(candles)):
            prev_close = candles[i - 1]['close']
            curr_close = candles[i]['close']

            # Защита от деления на ноль и невалидных данных
            if prev_close is None or curr_close is None or prev_close <= 0 or curr_close <= 0:
                continue

            log_rets.append(math.log(curr_close / prev_close))

        #log_rets = [c['close'] for c in candles[-self.min_candles:]]

        # 2. Берём последние 50 доходностей
        window = self.min_candles-1
        if len(log_rets) < window:
            return {}

        recent = log_rets[-window:]
        n = len(recent)
        mean = sum(recent) / n

        # 3. Центральные моменты
        m2 = sum((x - mean) ** 2 for x in recent) / n
        if m2 < 1e-12:  # Защита от деления на околонулевую дисперсию
            return {}

        m3 = sum((x - mean) ** 3 for x in recent) / n
        m4 = sum((x - mean) ** 4 for x in recent) / n

        # 4. Skew и Excess Kurtosis (Фишер)
        skew = m3 / (m2 ** 1.5)
        kurt = (m4 / (m2 ** 2)) - 3.0

        return {
            "skew_200": round(skew, 4),
            "kurt_excess_200": round(kurt, 4)
        }


@register_metric
class Pullback20Metric(PythonMetric):
    """Откат цены от локального максимума за окно."""
    name = "pullback_20"
    description = "Pullback % от max(close) за 20 свечей"
    min_candles = 20

    @property
    def min_candles(self) -> int:
        return 20

    def calculate_python(self, candles: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        if len(candles) < self.min_candles:
            return {}

        closes = [c['close'] for c in candles[-self.min_candles:]]
        max_close = max(closes)
        current_close = closes[-1]

        if max_close <= 0:
            return {}

        pullback = (max_close - current_close) / max_close
        return {"pullback_20": round(pullback, 4)}


@register_metric
class EMA50Metric(PythonMetric):
    """Экспоненциальная скользящая средняя (EMA) c периодом 50"""
    name = "ema_50"
    description = "EMA(50) цены закрытия"
    period=50

    @property
    def min_candles(self) -> int:
        # Математически для adjust=False достаточно 1 свечи,
        # но первые ~span значений сильно смещены из-за отсутствия истории.
        # Для сходимости нужно Period*2, чтобы отдавать адекватное значение.
        return 100

    def calculate_python(self, candles: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        if len(candles) < self.min_candles:
            return {}

        closes = [c['close'] for c in candles[-self.min_candles:]]
        alpha = 2.0 / (self.period + 1)  # α = 2 / (50 + 1) ≈ 0.039215686

        # Инициализация: EMA[0] = price[0] (строго соответствует adjust=False)
        ema = closes[0]

        # Рекуррентное обновление по всем ценам4
        for price in closes[1:]:
            ema = price * alpha + ema * (1 - alpha)

        return {"ema_50": round(ema, 4)}

@register_metric
class ClosePrice(PythonMetric):
    """Экспоненциальная скользящая средняя (EMA) c периодом 50"""
    name = "close_price"
    description = "Just a close price"

    @property
    def min_candles(self) -> int:
        return 1

    def calculate_python(self, candles: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        if len(candles) < self.min_candles:
            return {}

        return {"close_price": candles[-1]['close']}