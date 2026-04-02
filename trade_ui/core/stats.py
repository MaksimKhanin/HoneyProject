# core/stats.py
import pandas as pd
import numpy as np


# =============================================================================
# БАЗОВЫЕ ФУНКЦИИ
# =============================================================================

def calculate_price_type(df, price_type):
    """Считаем цену по выбранному алгоритму"""
    if price_type == "Close":
        return df['close']
    elif price_type == "(Low+High)/2":
        return (df['low'] + df['high']) / 2
    elif price_type == "(Low+High+Close)/3":
        return (df['low'] + df['high'] + df['close']) / 3
    elif price_type == "(Low+High+Close+Open)/4":
        return (df['low'] + df['high'] + df['close'] + df['open']) / 4
    return df['close']


def normalize_returns(df, price_col_name='price'):
    """Приводим все графики к виду: начало = 100%"""
    df_norm = df.copy()
    df_norm['norm_price'] = df_norm.groupby('ticker')[price_col_name].transform(
        lambda x: (x / x.iloc[0]) * 100
    )
    return df_norm


def subtract_benchmark(df, benchmark_list):
    """Вычитаем среднее бенчмарков из всех инструментов"""
    if not benchmark_list:
        return df

    bench_data = df[df['ticker'].isin(benchmark_list)][['time', 'norm_price']].copy()
    if bench_data.empty:
        return df

    bench_avg = bench_data.groupby('time')['norm_price'].mean().reset_index()
    bench_avg.rename(columns={'norm_price': 'bench_price'}, inplace=True)

    df_merged = pd.merge(df, bench_avg, on='time', how='left')
    df_merged['norm_price'] = df_merged['norm_price'] - df_merged['bench_price'] + 100

    return df_merged


# =============================================================================
# СКОЛЬЗЯЩАЯ СТАТИСТИКА
# =============================================================================

def calculate_rolling_mean(series, window=20):
    """Скользящая средняя"""
    return series.rolling(window=window, min_periods=1).mean()


def calculate_rolling_std(series, window=20):
    """Скользящее стандартное отклонение (σ)"""
    return series.rolling(window=window, min_periods=1).std()


def calculate_rolling_mad(series, window=20):
    """
    Скользящее среднее абсолютное отклонение (MAD) — по Талебу
    """

    def mad_func(x):
        if len(x) < 2:
            return 0
        mean = x.mean()
        return np.mean(np.abs(x - mean))

    return series.rolling(window=window, min_periods=1).apply(mad_func, raw=False)


def calculate_rolling_z_score(series, window=20):
    """Скользящий Z-score"""
    rolling_mean = calculate_rolling_mean(series, window)
    rolling_std = calculate_rolling_std(series, window)
    rolling_std = rolling_std.replace(0, np.nan)
    z_score = (series - rolling_mean) / rolling_std
    return z_score


def calculate_rolling_bands(series, window=20, n_std=3, method='std'):
    """Скользящие полосы отклонений"""
    rolling_mean = calculate_rolling_mean(series, window)

    if method == 'std':
        rolling_dev = calculate_rolling_std(series, window)
        suffix = 'σ'
    else:
        rolling_dev = calculate_rolling_mad(series, window)
        suffix = 'MAD'

    result = pd.DataFrame({
        'mean': rolling_mean,
        f'+1{suffix}': rolling_mean + 1 * rolling_dev,
        f'-1{suffix}': rolling_mean - 1 * rolling_dev,
        f'+2{suffix}': rolling_mean + 2 * rolling_dev,
        f'-2{suffix}': rolling_mean - 2 * rolling_dev,
        f'+3{suffix}': rolling_mean + 3 * rolling_dev,
        f'-3{suffix}': rolling_mean - 3 * rolling_dev,
    })

    return result


def calculate_deviation_from_mean(df, price_col='price', window=20, method='std'):
    """Считает СКОЛЬЗЯЩИЕ отклонения от средней для каждого тикера"""
    result = []

    for ticker in df['ticker'].unique():
        df_ticker = df[df['ticker'] == ticker].copy()
        prices = df_ticker[price_col]

        bands = calculate_rolling_bands(prices, window=window, method=method)

        for col in bands.columns:
            df_ticker[f'stat_{col}'] = bands[col].values

        df_ticker['z_score'] = calculate_rolling_z_score(prices, window=window).values
        df_ticker['method'] = method
        df_ticker['window'] = window
        result.append(df_ticker)

    return pd.concat(result, ignore_index=True)


def calculate_percentiles(series, percentiles=[25, 50, 75]):
    """Процентили распределения (глобальные)"""
    return {f'{p}%': np.percentile(series, p) for p in percentiles}


def calculate_rolling_stats(series, window=20):
    """Скользящая статистика — для понимания тренда"""
    rolling_mean = series.rolling(window=window, min_periods=1).mean()
    rolling_std = series.rolling(window=window, min_periods=1).std()

    return {
        'rolling_mean': rolling_mean,
        'rolling_std': rolling_std,
        'upper_band': rolling_mean + 2 * rolling_std,
        'lower_band': rolling_mean - 2 * rolling_std
    }


def calculate_skewness(series, window=20):
    """Скользящая скошенность (Skewness)"""

    def skew_func(x):
        if len(x) < 3:
            return 0
        return pd.Series(x).skew()

    return series.rolling(window=window, min_periods=1).apply(skew_func, raw=False)


def calculate_kurtosis(series, window=20):
    """Скользящий эксцесс (Kurtosis) — Fisher (норма = 0)"""

    def kurt_func(x):
        if len(x) < 4:
            return 0
        return pd.Series(x).kurtosis()

    return series.rolling(window=window, min_periods=1).apply(kurt_func, raw=False)


# =============================================================================
# ТОРГОВЫЕ СИГНАЛЫ
# =============================================================================

def generate_trading_signal(prices, window=20):
    """
    Генерирует торговый сигнал на основе статистики

    ВАЖНО: Считаем СКОЛЬЗЯЩИЕ метрики для ПОСЛЕДНЕЙ свечи,
    а не глобальные за всё окно!
    """
    if len(prices) < window:
        return {
            'signal': 'NO DATA',
            'confidence': 0,
            'z_score': np.nan,
            'skewness': np.nan,
            'kurtosis': np.nan,
            'stop_multiplier': 1.0,
            'reason': 'Недостаточно данных'
        }

    # Убеждаемся что цены отсортированы по времени (возрастание)
    prices = prices.reset_index(drop=True)

    # Берём последние window + 1 свечей для расчёта скользящих метрик
    prices_window = prices.tail(window + 10).reset_index(drop=True)

    current_price = prices.iloc[-1]

    # =====================================================================
    # СКОЛЬЗЯЩИЕ МЕТРИКИ ДЛЯ ПОСЛЕДНЕЙ СВЕЧИ (как на странице 2!)
    # =====================================================================

    # Скользящая средняя и std для Z-score
    rolling_mean = prices_window.rolling(window=window, min_periods=1).mean()
    rolling_std = prices_window.rolling(window=window, min_periods=1).std()

    # Z-score для последней свечи
    last_mean = rolling_mean.iloc[-1]
    last_std = rolling_std.iloc[-1]

    if last_std == 0 or pd.isna(last_std):
        return {
            'signal': 'HOLD',
            'confidence': 0,
            'z_score': 0,
            'skewness': 0,
            'kurtosis': 0,
            'stop_multiplier': 1.0,
            'reason': 'Нулевая волатильность'
        }

    z_score = (current_price - last_mean) / last_std

    # =====================================================================
    # СКОЛЬЗЯЩИЕ Skewness и Kurtosis (как на странице 2!)
    # =====================================================================

    def rolling_skew(x):
        if len(x) < 3:
            return 0
        return pd.Series(x).skew()

    def rolling_kurt(x):
        if len(x) < 4:
            return 0
        return pd.Series(x).kurtosis()  # Fisher: норма = 0

    # Считаем скользящие метрики
    skew_series = prices_window.rolling(window=window, min_periods=1).apply(rolling_skew, raw=False)
    kurt_series = prices_window.rolling(window=window, min_periods=1).apply(rolling_kurt, raw=False)

    # Берём значения для ПОСЛЕДНЕЙ свечи
    skew = skew_series.iloc[-1]
    kurt = kurt_series.iloc[-1]

    # =====================================================================
    # ГЕНЕРАЦИЯ СИГНАЛА
    # =====================================================================

    signal = "HOLD"
    confidence = 50
    stop_multiplier = 1.5
    reasons = []

    # Базовый сигнал по Z-score
    if z_score < -2:
        signal = "BUY"
        reasons.append(f"Цена ниже средней на {abs(z_score):.1f}σ")
    elif z_score > 2:
        signal = "SELL"
        reasons.append(f"Цена выше средней на {abs(z_score):.1f}σ")

    # Корректировка по скошенности
    if skew > 1:
        if signal == "BUY":
            confidence += 20
            reasons.append("Перекос вверх — лонг надёжнее (рынок растёт)")
        elif signal == "SELL":
            confidence -= 30
            reasons.append("Перекос вверх — шорт ОПАСЕН! (тренд вверх)")
    elif skew < -1:
        if signal == "SELL":
            confidence += 20
            reasons.append("Перекос вниз — шорт надёжнее (рынок падает)")
        elif signal == "BUY":
            confidence -= 30
            reasons.append("Перекос вниз — лонг ОПАСЕН! (тренд вниз)")

    # Корректировка по эксцессу
    if kurt > 3:
        confidence -= 30
        stop_multiplier = 3.0
        reasons.append("🚨 Очень жирные хвосты — ОПАСНО!")
    elif kurt > 0:
        confidence -= 15
        stop_multiplier = 2.0
        reasons.append("Жирные хвосты — увеличь стоп")
    elif kurt < -0.5:
        confidence += 15
        stop_multiplier = 1.0
        reasons.append("Тонкие хвосты — можно агрессивнее")

    # Экстремальные значения
    if abs(z_score) > 3:
        reasons.append("⚡ ЭКСТРЕМУМ!")

    # Ограничиваем confidence
    confidence = max(0, min(100, confidence))

    # Финальное решение
    if confidence < 40:
        signal = "HOLD"
    elif confidence >= 70:
        signal = "STRONG " + signal

    return {
        'signal': signal,
        'confidence': confidence,
        'z_score': round(float(z_score), 2),
        'skewness': round(float(skew), 2),
        'kurtosis': round(float(kurt), 2),
        'stop_multiplier': stop_multiplier,
        'reason': '; '.join(reasons) if reasons else 'Нет явных сигналов'
    }


def calculate_bollinger_bands(series, window=20, n_std=2):
    rolling_mean = series.rolling(window=window, min_periods=1).mean()
    rolling_std = series.rolling(window=window, min_periods=1).std()

    return pd.DataFrame({
        'upper': rolling_mean + n_std * rolling_std,
        'middle': rolling_mean,
        'lower': rolling_mean - n_std * rolling_std,
        'width': (rolling_mean + n_std * rolling_std) - (rolling_mean - n_std * rolling_std),
        'width_pct': ((rolling_mean + n_std * rolling_std) - (rolling_mean - n_std * rolling_std)) / rolling_mean * 100
    })


def calculate_atr(df, window=14):
    """
    Average True Range — средняя истинная волатильность
    Учитывает гэпы и лимиты
    """
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)

    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=window).mean()

    return atr


def detect_volatility_squeeze(series, window=20, lookback=60):
    """
    Обнаружение сжатия волатильности

    Возвращает:
    - squeeze: True/False (волатильность на минимуме)
    - squeeze_strength: 0-100 (насколько сильно сжато)
    - percentile: процентиль текущей волатильности за lookback
    """
    # Ширина Боллинджера в %
    bb = calculate_bollinger_bands(series, window=window)
    bb_width_pct = bb['width_pct']

    # Процентиль текущей ширины за последние lookback периодов
    current_width = bb_width_pct.iloc[-1]
    historical_widths = bb_width_pct.tail(lookback)

    percentile = (historical_widths < current_width).sum() / len(historical_widths) * 100

    # Сжатие = волатильность в нижних 20% за период
    squeeze = percentile < 20
    squeeze_strength = 100 - percentile  # Чем меньше волатильность, тем сильнее сжатие

    return {
        'squeeze': squeeze,
        'squeeze_strength': round(squeeze_strength, 2),
        'percentile': round(percentile, 2),
        'current_width_pct': round(current_width, 4)
    }



def calculate_volume_analysis(df, price_column='close', window=20):
    """
    Анализ объёмов для обнаружения накопления

    Требует колонки 'volume' в DataFrame
    """
    if 'volume' not in df.columns:
        return None

    volume = df['volume']
    close = df[price_column]

    # Средний объём
    avg_volume = volume.rolling(window=window).mean()

    # Отношение текущего объёма к среднему
    volume_ratio = volume / avg_volume

    # OBV (On-Balance Volume)
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()

    # Сигналы
    current_volume_ratio = volume_ratio.iloc[-1]
    volume_spike = current_volume_ratio > 1.5  # > 150% от среднего

    # Накопление: OBV растёт при флэте цены
    obv_trend = obv.diff(window).iloc[-1] > 0
    price_flat = abs(close.iloc[-1] - close.iloc[-window]) / close.iloc[-window] < 0.05  # < 5% за период

    accumulation = obv_trend and price_flat

    return {
        'volume_ratio': round(current_volume_ratio, 2),
        'volume_spike': volume_spike,
        'obv': obv.iloc[-1],
        'obv_trend': 'UP' if obv_trend else 'DOWN',
        'accumulation': accumulation,
        'avg_volume': round(avg_volume.iloc[-1], 0)
    }


def calculate_vwap(df):
    """
    Volume Weighted Average Price
    Цена, взвешенная по объёму
    """
    if 'volume' not in df.columns:
        return None

    typical_price = (df['high'] + df['low'] + df['close']) / 3
    vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()

    return vwap


def find_pivot_levels(series, window=5):
    """
    Поиск локальных максимумов и минимумов (Pivot Points)

    window: количество свечей слева и справа для подтверждения
    """
    df = pd.DataFrame({'price': series})

    # Локальные максимумы
    df['is_high'] = (df['price'] == df['price'].rolling(window=2 * window + 1, center=True).max())
    # Локальные минимумы
    df['is_low'] = (df['price'] == df['price'].rolling(window=2 * window + 1, center=True).min())

    # Уровни сопротивления (максимумы)
    resistance_levels = df[df['is_high']]['price'].tail(5).tolist()

    # Уровни поддержки (минимумы)
    support_levels = df[df['is_low']]['price'].tail(5).tolist()

    return {
        'resistance': resistance_levels,
        'support': support_levels
    }


from sklearn.cluster import KMeans


def find_price_clusters(series, n_clusters=5):
    """
    Находит ценовые уровни где цена проводила больше всего времени
    Аналог Volume Profile но без объёма

    Возвращает:
    - levels: отсортированные уровни кластеров
    - counts: количество свечей в каждом кластере
    - strongest_level: уровень с максимальным количеством свечей
    - cluster_centers: центры кластеров
    """
    if len(series) < n_clusters:
        return None

    prices = series.values.reshape(-1, 1)

    # Кластеризуем цены
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, max_iter=300)
    kmeans.fit(prices)

    # Центры кластеров = уровни
    levels = sorted(kmeans.cluster_centers_.flatten())

    # Количество свечей в каждом кластере
    labels = kmeans.labels_
    counts = np.bincount(labels)

    # Находим самый сильный уровень (где цена была чаще всего)
    strongest_idx = np.argmax(counts)
    strongest_level = levels[strongest_idx]

    return {
        'levels': levels,
        'counts': counts,
        'strongest_level': strongest_level,
        'cluster_centers': kmeans.cluster_centers_.flatten(),
        'labels': labels
    }


def find_price_clusters_series(series, n_clusters=5, rolling_window=60):
    """
    Скользящая кластеризация цен для каждой точки

    Возвращает DataFrame с уровнями для каждой свечи
    """
    if len(series) < rolling_window:
        return None

    results = []

    for i in range(len(series)):
        if i < rolling_window:
            window_data = series.iloc[:i + 1]
        else:
            window_data = series.iloc[i - rolling_window:i + 1]

        if len(window_data) < n_clusters:
            results.append({
                'levels': [],
                'strongest_level': np.nan,
                'n_clusters': 0
            })
            continue

        clusters = find_price_clusters(window_data, n_clusters=n_clusters)

        if clusters is None:
            results.append({
                'levels': [],
                'strongest_level': np.nan,
                'n_clusters': 0
            })
        else:
            results.append({
                'levels': clusters['levels'],
                'strongest_level': clusters['strongest_level'],
                'n_clusters': len(clusters['levels'])
            })

    return results


def detect_volatility_squeeze_series(series, window=20):
    bb = calculate_bollinger_bands(series, window=window)
    bb_width_pct = bb['width_pct']

    lookback=window*3

    percentiles = []
    for i in range(len(bb_width_pct)):
        if i < lookback:
            historical = bb_width_pct.iloc[:i + 1]
        else:
            historical = bb_width_pct.iloc[i - lookback:i + 1]

        percentile = (historical < bb_width_pct.iloc[i]).sum() / len(historical) * 100
        percentiles.append(percentile)

    bb_width_pct = bb_width_pct.reset_index(drop=True)
    percentiles = pd.Series(percentiles)

    squeeze = percentiles < 20
    squeeze_strength = 100 - percentiles

    return pd.DataFrame({
        'bb_width_pct': bb_width_pct.values,
        'squeeze_percentile': percentiles.values,
        'squeeze': squeeze.values,
        'squeeze_strength': squeeze_strength.values
    })


def calculate_volume_analysis_series(df, price_column='close', window=20):
    if 'volume' not in df.columns:
        return None

    volume = df['volume']
    close = df[price_column]

    avg_volume = volume.rolling(window=window, min_periods=1).mean()
    volume_ratio = volume / avg_volume
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()

    # 2. Улучшенный OBV (классический)
    # Если цена выросла -> +Volume, упала -> -Volume, равна -> 0
    price_diff = close.diff()
    obv = np.where(price_diff > 0, volume, np.where(price_diff < 0, -volume, 0))
    obv = pd.Series(obv, index=df.index).cumsum()

    # 3. Изменения за период
    obv_change = obv.diff(window) # Изменение OBV за window
    price_change_pct = close.pct_change(window) # Процентное изменение цены

    # 4. Адаптивный порог волатильности (вместо жестких 0.05)
    # Используем ATR или просто стандартное отклонение цены за период
    price_volatility = close.rolling(window).std() / close.rolling(window).mean()
    # Считаем накоплением, если движение цены меньше 1 стандартного отклонения (боковик)
    is_consolidation = abs(price_change_pct) < (price_volatility * 1.5)

    # 5. Финальная логика
    # 1. OBV растет (покупатели активны)
    # 2. Цена в боковике (не ушла далеко)
    # 3. Объем выше среднего (интерес к инструменту)
    accumulation = (
        (obv_change > 0) &
        (is_consolidation) &
        (volume_ratio > 1.0) # Хотя бы средний объем
    )

    #price_change = close.rolling(window=window).apply(
    #    lambda x: (x.iloc[-1] - x.iloc[0]) / x.iloc[0] if len(x) > 1 else 0)
    #obv_change = obv.rolling(window=window).apply(lambda x: x.iloc[-1] - x.iloc[0] if len(x) > 1 else 0)

    #accumulation = (obv_change > 0) & (abs(price_change) < 0.05)

    return pd.DataFrame({
        'volume': volume.values,
        'avg_volume': avg_volume.values,
        'volume_ratio': volume_ratio.values,
        'volume_spike': (volume_ratio > 1.5).values,
        'obv': obv.values,
        'accumulation': accumulation.values
    })


def find_volume_nodes(df, n_bins=50):
    """
    Volume Profile: находит ценовые зоны с максимальным объёмом

    Возвращает:
    - POC (Point of Control): уровень с максимальным объёмом
    - Value Area: 70% объёма вокруг POC
    """
    if 'volume' not in df.columns:
        return None

    # Биним цены
    min_price = df['low'].min()
    max_price = df['high'].max()
    bins = np.linspace(min_price, max_price, n_bins)

    # Суммируем объём в каждом бине
    volume_by_price = []
    for i in range(len(bins) - 1):
        mask = (df['close'] >= bins[i]) & (df['close'] < bins[i + 1])
        vol = df.loc[mask, 'volume'].sum()
        volume_by_price.append({
            'price_level': (bins[i] + bins[i + 1]) / 2,
            'volume': vol
        })

    vol_df = pd.DataFrame(volume_by_price)

    # POC
    poc = vol_df.loc[vol_df['volume'].idxmax(), 'price_level']

    # Value Area (70% объёма)
    total_volume = vol_df['volume'].sum()
    vol_df = vol_df.sort_values('volume', ascending=False)
    vol_df['cumsum'] = vol_df['volume'].cumsum()
    value_area = vol_df[vol_df['cumsum'] <= total_volume * 0.7]['price_level']

    return {
        'poc': round(poc, 2),
        'value_area_high': round(value_area.max(), 2),
        'value_area_low': round(value_area.min(), 2),
        'total_volume': total_volume
    }


def detect_consolidation(df, window=20):
    """
    Обнаружение консолидации (флэта)

    Признаки:
    - ADX < 25 (нет тренда)
    - Цена в канале < 5%
    - Низкая волатильность
    """
    close = df['close']
    high = df['high']
    low = df['low']

    # 1. ADX (упрощённая версия)
    def calculate_adx(df, window=14):
        high = df['high']
        low = df['low']
        close = df['close']

        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(window=window).mean()
        plus_di = 100 * (plus_dm.rolling(window=window).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=window).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=window).mean()

        return adx

    adx = calculate_adx(df, window=window)
    current_adx = adx.iloc[-1] if not adx.empty else 50

    # 2. Ширина канала
    highest = close.rolling(window=window).max()
    lowest = close.rolling(window=window).min()
    channel_width = (highest - lowest) / lowest * 100
    current_channel_width = channel_width.iloc[-1]

    # 3. Волатильность
    volatility = close.rolling(window=window).std() / close.rolling(window=window).mean() * 100
    current_volatility = volatility.iloc[-1]

    # Консолидация = нет тренда + узкий канал + низкая волатильность
    is_consolidation = (
            (current_adx < 25) and
            (current_channel_width < 5) and
            (current_volatility < 3)
    )

    return {
        'is_consolidation': is_consolidation,
        'adx': round(current_adx, 2),
        'channel_width_pct': round(current_channel_width, 2),
        'volatility_pct': round(current_volatility, 2),
        'resistance': round(highest.iloc[-1], 2),
        'support': round(lowest.iloc[-1], 2)
    }


def detect_breakout_setup(df, price_column='close', window=20):
    """
    Комплексный детектор готовности к пробою tr

    Сигнал = Сжатие волатильности + Накопление объёма + Цена у уровня
    """
    close = df[price_column]

    # 1. Сжатие волатильности
    squeeze = detect_volatility_squeeze(close, window=window)

    # 2. Анализ объёма
    volume_analysis = calculate_volume_analysis(df, window=window)

    # 3. Консолидация
    consolidation = detect_consolidation(df, window=window)

    # 4. Уровень сопротивления/поддержки
    pivots = find_pivot_levels(close, window=5)
    current_price = close.iloc[-1]

    # Расстояние до ближайшего уровня
    if pivots['resistance']:
        dist_to_resistance = (min(pivots['resistance']) - current_price) / current_price * 100
    else:
        dist_to_resistance = 999

    if pivots['support']:
        dist_to_support = (current_price - max(pivots['support'])) / current_price * 100
    else:
        dist_to_support = 999

    # Цена рядом с уровнем (< 2%)
    near_level = min(dist_to_resistance, dist_to_support) < 2

    # === КОМПЛЕКСНЫЙ СИГНАЛ ===
    breakout_ready = (
            squeeze['squeeze_strength'] > 70 and  # Сильное сжатие
            volume_analysis and volume_analysis['accumulation'] and  # Накопление
            consolidation['is_consolidation'] and  # Консолидация
            near_level  # Цена у уровня
    )

    # Направление вероятного пробоя
    if volume_analysis and volume_analysis['obv_trend'] == 'UP':
        probable_direction = 'UP'
    elif volume_analysis and volume_analysis['obv_trend'] == 'DOWN':
        probable_direction = 'DOWN'
    else:
        probable_direction = 'UNKNOWN'

    return {
        'breakout_ready': breakout_ready,
        'confidence': round(
            (squeeze['squeeze_strength'] +
             (volume_analysis['volume_ratio'] * 20 if volume_analysis else 0) +
             (50 if consolidation['is_consolidation'] else 0) +
             (50 if near_level else 0)) / 4, 2
        ),
        'squeeze_strength': squeeze['squeeze_strength'],
        'accumulation': volume_analysis['accumulation'] if volume_analysis else False,
        'consolidation': consolidation['is_consolidation'],
        'near_level': near_level,
        'probable_direction': probable_direction,
        'resistance': min(pivots['resistance']) if pivots['resistance'] else None,
        'support': max(pivots['support']) if pivots['support'] else None,
        'dist_to_resistance_pct': round(dist_to_resistance, 2),
        'dist_to_support_pct': round(dist_to_support, 2)
    }


def find_pivot_levels_series(series, window=5):
    df = pd.DataFrame({'price': series})

    df['is_high'] = (df['price'] == df['price'].rolling(window=2 * window + 1, center=True, min_periods=1).max())
    df['is_low'] = (df['price'] == df['price'].rolling(window=2 * window + 1, center=True, min_periods=1).min())

    df['resistance'] = df.loc[df['is_high'], 'price'].ffill()
    df['support'] = df.loc[df['is_low'], 'price'].ffill()

    return df[['resistance', 'support', 'is_high', 'is_low']]


def detect_consolidation_series(df, window=20):
    close = df['close']
    high = df['high']
    low = df['low']

    def calculate_adx_series(df, window=14):
        high = df['high']
        low = df['low']
        close = df['close']

        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(window=window, min_periods=1).mean()
        plus_di = 100 * (plus_dm.rolling(window=window, min_periods=1).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=window, min_periods=1).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001)
        adx = dx.rolling(window=window, min_periods=1).mean()

        return adx

    adx = calculate_adx_series(df, window=14)

    highest = close.rolling(window=window, min_periods=1).max()
    lowest = close.rolling(window=window, min_periods=1).min()
    channel_width = (highest - lowest) / lowest * 100

    volatility = close.rolling(window=window, min_periods=1).std() / close.rolling(window=window,
                                                                                   min_periods=1).mean() * 100

    is_consolidation = (adx < 25) & (channel_width < 5) & (volatility < 3)

    return pd.DataFrame({
        'adx': adx.values,
        'channel_width_pct': channel_width.values,
        'volatility_pct': volatility.values,
        'is_consolidation': is_consolidation.values,
        'resistance': highest.values,
        'support': lowest.values
    })


def detect_breakout_setup_series(df, price_column='close', window=20):
    close = df[price_column]

    squeeze = detect_volatility_squeeze_series(close, window=window)
    volume_analysis = calculate_volume_analysis_series(df, window=window)
    consolidation = detect_consolidation_series(df, window=window)
    pivots = find_pivot_levels_series(close, window=5)

    dist_to_resistance = (pivots['resistance'] - close) / close * 100
    dist_to_support = (close - pivots['support']) / close * 100
    near_level = (dist_to_resistance.abs() < 2) | (dist_to_support.abs() < 2)

    if volume_analysis is not None:
        obv_trend = pd.Series(volume_analysis['obv']).diff(window) > 0
        probable_direction = pd.Series(['UNKNOWN'] * len(df))
        probable_direction[obv_trend] = 'UP'
        probable_direction[~obv_trend] = 'DOWN'
    else:
        probable_direction = pd.Series(['UNKNOWN'] * len(df))

    if volume_analysis is not None:
        breakout_ready = (
                (squeeze['squeeze_strength'] > 70) &
                (volume_analysis['accumulation']) &
                (consolidation['is_consolidation']) &
                (near_level)
        )
    else:
        breakout_ready = (
                (squeeze['squeeze_strength'] > 70) &
                (consolidation['is_consolidation']) &
                (near_level)
        )

    result = pd.DataFrame({
        'breakout_ready': breakout_ready.values,
        'squeeze_strength': squeeze['squeeze_strength'].values,
        'consolidation': consolidation['is_consolidation'].values,
        'near_level': near_level.values,
        'probable_direction': probable_direction.values
    })

    if volume_analysis is not None:
        result['accumulation'] = volume_analysis['accumulation'].values

    return result