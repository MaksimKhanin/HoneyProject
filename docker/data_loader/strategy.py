# strategy.py

from collections import deque
import math
from typing import List, Dict, Optional, Tuple

# 📚 РЕЕСТР СТРАТЕГИЙ (тот же интерфейс)
STRATEGY_REGISTRY = {
    "none": "❌ Нет стратегии (только сбор данных)",
    "sma_cross": "📈 SMA Cross (Пересечение средних)",
    "rsi_oversold": "📉 RSI (Перепроданность/Перекупленность)",
    "momentum": "🚀 Momentum (Импульс цены)",
    "bollinger": "📦 Bollinger Breakout (Пробой полос)",
}

def _decimal_digits(number):
    count_after_decimal = str(number)[::-1].find('.')
    return count_after_decimal

def get_price_type(candles: List[Dict], price_type: str = "Close") -> List[float]:
    """
    Возвращает список цен нужного типа из списка свечей.

    :param candles: список словарей [{'open':..., 'high':..., 'low':..., 'close':...}, ...]
    :param price_type: тип цены ("Close", "LH_Avg", "LHC_Avg", "LHCO_Avg")
    :return: список чисел (цен)
    """
    prices = []

    digits = _decimal_digits(candles[0]['close'])

    for c in candles:
        if price_type == "Close":
            val = c['close']
        elif price_type == "LH_Avg":  # (Low+High)/2
            val = (c['low'] + c['high']) / 2.0
        elif price_type == "LHC_Avg":  # (Low+High+Close)/3 (Typical Price)
            val = (c['low'] + c['high'] + c['close']) / 3.0
        elif price_type == "LHCO_Avg":  # (Low+High+Close+Open)/4
            val = (c['low'] + c['high'] + c['close'] + c['open']) / 4.0
        else:
            val = c['close']  # дефолт

        prices.append(round(val, digits))

    return prices


# 🛠 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (чистый Python)

def calc_sma(values: List[float], period: int) -> float:
    """Простая скользящая средняя. На пальцах: сложили последние N цен, поделили на N."""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def calc_rsi(closes: List[float], period: int = 14) -> float:
    """
    RSI на минималках.
    Считаем средние приросты и падения, потом нормируем в 0-100.
    """
    if len(closes) < period + 1:
        return None

    # Считаем изменения цены
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Берем последние 'period' изменений
    recent = deltas[-period:]

    gains = [d if d > 0 else 0 for d in recent]
    losses = [-d if d < 0 else 0 for d in recent]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100  # Если только росли — перегрев

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calc_std(values: List[float], period: int) -> float:
    """Стандартное отклонение (для Боллинджера). Мера волатильности."""
    if len(values) < period:
        return None
    subset = values[-period:]
    mean = sum(subset) / period
    variance = sum((x - mean) ** 2 for x in subset) / period
    return math.sqrt(variance)

def calc_mad(values: List[float], period: int) -> float:
    """Стандартное отклонение (для Боллинджера). Мера волатильности."""
    if len(values) < period:
        return None
    subset = values[-period:]
    mean = sum(subset) / period
    abs_deviations = [abs(x - mean) for x in subset]
    mad = sum(abs_deviations) / period
    return mad


# =============================================================================
# 🔥 МОМЕНТЫ РАСПРЕДЕЛЕНИЯ (Skewness, Kurtosis)
# =============================================================================

def calc_skewness(values: List[float], period: Optional[int] = None) -> Optional[float]:
    """
    🔥 Скошенность (асимметрия распределения).

    Интерпретация:
    - 0 = симметричное распределение (нормальное)
    - >0 = правосторонняя асимметрия (длинный хвост вправо, больше высоких значений)
    - <0 = левосторонняя асимметрия (длинный хвост влево, больше низких значений)

    Для трейдинга:
    - Положительная скошенность цен → вероятность резких скачков вверх
    - Отрицательная скошенность → риск резких падений

    :return: коэффициент скошенности или None
    """
    if not values:
        return None

    subset = values[-period:] if period else values
    n = len(subset)

    if n < 3:  # Нужно минимум 3 точки для оценки асимметрии
        return None

    mean = sum(subset) / n
    std = calc_std(subset)

    if std is None or std == 0:
        return 0.0

    # Третий центральный момент, нормированный на куб std
    skew = sum((x - mean) ** 3 for x in subset) / n
    skew = skew / (std ** 3)

    return skew


def calc_kurtosis(values: List[float], period: Optional[int] = None,
                  excess: bool = True) -> Optional[float]:
    """
    🔥 Эксцесс (островершинность распределения).

    Интерпретация (excess=True):
    - 0 = нормальное распределение (Гаусс)
    - >0 = остроконечное, "тяжёлые хвосты" (больше экстремумов, чем у нормального)
    - <0 = плосковершинное (меньше экстремумов)

    Для трейдинга:
    - Высокий эксцесс → больше "чёрных лебедей", риск резких движений
    - Низкий эксцесс → цена движется предсказуемо, мало выбросов

    :param excess: если True — возвращает "избыточный эксцесс" (kurtosis - 3)
    :return: коэффициент эксцесса или None
    """
    if not values:
        return None

    subset = values[-period:] if period else values
    n = len(subset)

    if n < 4:  # Нужно минимум 4 точки для оценки эксцесса
        return None

    mean = sum(subset) / n
    std = calc_std(subset)

    if std is None or std == 0:
        return 0.0

    # Четвёртый центральный момент, нормированный на 4-ю степень std
    kurt = sum((x - mean) ** 4 for x in subset) / n
    kurt = kurt / (std ** 4)

    # Избыточный эксцесс (относительно нормального распределения)
    if excess:
        kurt = kurt - 3.0

    return kurt


# =============================================================================
# 🔥 Z-SCORE (стандартизация)
# =============================================================================

def calc_z_score(value: float, mean: float, std: float) -> Optional[float]:
    """
    🔥 Z-score для одного значения.
    Показывает, на сколько стандартных отклонений значение отстоит от среднего.

    Интерпретация:
    - |Z| < 1 = в пределах 1 сигмы (68% вероятности, нормальное значение)
    - |Z| < 2 = в пределах 2 сигм (95% вероятности)
    - |Z| > 2 = выброс (5% вероятность, аномалия)
    - |Z| > 3 = сильный выброс (0.3% вероятность, экстремум)

    Для трейдинга:
    - Z-score цены > 2 → цена аномально высока (возможно, пора продавать)
    - Z-score цены < -2 → цена аномально низка (возможно, пора покупать)

    :param value: текущее значение
    :param mean: среднее за период
    :param std: стандартное отклонение за период
    :return: Z-score или None
    """
    if std is None or std == 0:
        return None

    return (value - mean) / std


# =============================================================================
# 🔥 VOLATILITY SQUEEZE (сжатие волатильности)
# =============================================================================

def calculate_bollinger_width(values: List[float], window: int = 20,
                              std_mult: float = 2.0) -> Optional[Dict]:
    """
    Рассчитывает ширину полос Боллинджера в %.

    :return: словарь с метриками или None
    """
    if len(values) < window:
        return None

    subset = values[-window:]
    mean = sum(subset) / window
    std = calc_std(subset)

    if std is None or std == 0:
        return None

    upper = mean + (std_mult * std)
    lower = mean - (std_mult * std)
    width = upper - lower
    width_pct = (width / mean) * 100 if mean != 0 else 0

    return {
        'mean': mean,
        'std': std,
        'upper': upper,
        'lower': lower,
        'width': width,
        'width_pct': width_pct
    }

def detect_volatility_squeeze(values: List[float], window: int = 20,
                              lookback: int = 60) -> Optional[Dict]:
    """
    🔥 Обнаружение сжатия волатильности (адаптация без Pandas).

    Возвращает:
    - squeeze: True/False (волатильность на минимуме)
    - squeeze_strength: 0-100 (насколько сильно сжато)
    - percentile: процентиль текущей волатильности за lookback
    - current_width_pct: текущая ширина Боллинджера в %

    Логика:
    1. Считаем ширину Боллинджера для каждого из последних lookback периодов
    2. Находим процентиль текущей ширины относительно истории
    3. Если процентиль < 20% → волатильность в нижних 20% → сжатие

    Для трейдинга:
    - Сжатие волатильности → готовится сильный пробой (но неизвестно направление)
    - Можно использовать как фильтр для входа в стратегию пробоя
    """
    if len(values) < lookback:
        return None

    # 1. Считаем ширину Боллинджера для каждого периода в lookback
    widths = []
    for i in range(len(values) - lookback, len(values)):
        if i < window - 1:
            continue

        subset = values[i - window + 1:i + 1]
        bb = calculate_bollinger_width(subset, window=window)

        if bb:
            widths.append(bb['width_pct'])

    if len(widths) < 10:  # Нужно минимум данных для оценки
        return None

    # 2. Текущая ширина
    current_width = widths[-1]

    # 3. Процентиль: какой % исторических ширин МЕНЬШЕ текущей
    count_below = sum(1 for w in widths[:-1] if w < current_width)
    percentile = (count_below / (len(widths) - 1)) * 100

    # 4. Сжатие = волатильность в нижних 20%
    squeeze = percentile < 20
    squeeze_strength = 100 - percentile  # Чем меньше волатильность, тем сильнее сжатие

    return {
        'squeeze': squeeze,
        'squeeze_strength': round(squeeze_strength, 2),
        'percentile': round(percentile, 2),
        'current_width_pct': round(current_width, 4),
        'min_width_pct': round(min(widths), 4),
        'max_width_pct': round(max(widths), 4),
        'avg_width_pct': round(sum(widths) / len(widths), 4)
    }


# =============================================================================
# 🔥 УНИВЕРСАЛЬНЫЙ КАЛЬКУЛЯТОР (все метрики сразу)
# =============================================================================

def calc_distribution_stats(values: List[float], period: Optional[int] = None) -> Dict:
    """
    🔥 Рассчитывает все статистики распределения сразу.

    Удобно для логирования и сохранения в БД.
    """
    subset = values[-period:] if period else values

    return {
        'count': len(subset),
        'mean': calc_sma(subset),
        'std': calc_std(subset),
        'mad': calc_mad(subset),
        'skewness': calc_skewness(subset),
        'kurtosis': calc_kurtosis(subset, excess=True),
        'min': min(subset) if subset else None,
        'max': max(subset) if subset else None,
        'range': (max(subset) - min(subset)) if subset else None,
    }

# 🎯 СТРАТЕГИИ (принимают список цен, а не DataFrame!)

def strategy_none(closes: List[float], **kwargs) -> str:
    """Заглушка — ничего не делаем."""
    return ("HOLD", None)


def strategy_sma_cross(closes: List[float], fast: int = 9, slow: int = 21) -> tuple[str, None] | tuple[str, str]:
    """
    Пересечение двух скользящих средних.
    closes — список цен закрытия, последние = свежие.
    """
    if len(closes) < slow:
        return "WAIT", None

    # Считаем текущие и предыдущие значения средних
    prev_fast = calc_sma(closes[:-1], fast)
    curr_fast = calc_sma(closes, fast)
    prev_slow = calc_sma(closes[:-1], slow)
    curr_slow = calc_sma(closes, slow)

    if None in [prev_fast, curr_fast, prev_slow, curr_slow]:
        return "WAIT", None

    # Пересечение снизу вверх -> BUY
    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return "BUY", f"Быстрая SMA {curr_fast} пересекла медленную {curr_slow}"
    # Пересечение сверху вниз -> SELL
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return "SELL", f"Быстрая SMA {curr_fast} пересекла медленную {curr_slow}"

    return "HOLD", None


def strategy_rsi_oversold(closes: List[float], period: int = 14) -> tuple[str, None] | tuple[str, str]:
    """
    RSI стратегия: покупаем на дне (<30), продаем на пике (>70).
    """
    rsi = calc_rsi(closes, period)
    if rsi is None:
        return "WAIT", None

    if rsi < 30:
        return "BUY", f"Значение RSI {rsi}, что менее 30"
    elif rsi > 70:
        return "SELL", f"Значение RSI {rsi}, что более 30"
    return "HOLD", None


def strategy_momentum(closes: List[float], lookback: int = 3, threshold_pct: float = 0.5) -> tuple[str, None] | tuple[str, str]:
    """
    Импульс: если цена изменилась больше чем на threshold_pct% за lookback свечей.
    """
    if len(closes) < lookback + 1:
        return "WAIT", None

    old_price = closes[-(lookback + 1)]
    curr_price = closes[-1]
    change_pct = (curr_price - old_price) / old_price * 100

    if change_pct > threshold_pct:
        return "BUY", f"Рост цены актива более чем на {round(change_pct, 2)} за последние {lookback} свечек. {curr_price}vs{old_price}"
    elif change_pct < -threshold_pct:
        return "SELL", f"Падение цены актива более чем на {round(change_pct, 2)} за последние {lookback} свечек. {curr_price}vs{old_price}"
    return "HOLD", None


def strategy_bollinger(closes: List[float], period: int = 20, std_mult: float = 2.0) -> tuple[str, None] | tuple[str, str]:
    """
    Полосы Боллинджера: пробой нижней — покупка, верхней — продажа.
    """
    if len(closes) < period:
        return "WAIT", None

    sma = calc_sma(closes, period)
    std = calc_std(closes, period)

    if sma is None or std is None:
        return "WAIT", None

    upper = sma + std_mult * std
    lower = sma - std_mult * std
    curr = closes[-1]

    if curr < lower:
        return "BUY", f"Цена {curr} ниже нижней полосы {lower} — перепроданность"  # Цена ниже нижней полосы — перепроданность
    elif curr > upper:
        return "SELL" f"Цена {curr} выше нижней верхней {upper} — перекупленность"   # Цена выше верхней — перекупленность
    return "HOLD", None


# 🔄 УНИВЕРСАЛЬНЫЙ ЗАПУСКАТОР
STRATEGY_FUNCS = {
    "none": strategy_none,
    "sma_cross": strategy_sma_cross,
    "rsi_oversold": strategy_rsi_oversold,
    "momentum": strategy_momentum,
    "bollinger": strategy_bollinger,
}


def run_strategy(name: str, closes: List[float], **kwargs) -> str:
    """
    Запускает стратегию по имени.
    closes: список цен закрытия [старые ..., новые]
    """
    func = STRATEGY_FUNCS.get(name, strategy_none)
    try:
        return func(closes, **kwargs)
    except Exception as e:
        return f"ERROR:{str(e)}"