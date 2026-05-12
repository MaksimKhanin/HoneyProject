# pages/02_📊_Статистический_Анализ.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import datetime
import json
from pathlib import Path

from core.config import CONFIG_FILE_PAGE2 as CONFIG_FILE, DEFAULT_PREFS_PAGE2
from core.database import get_connection, fetch_candles
from core.stats import (
    calculate_price_type,
    calculate_rolling_z_score,
    calculate_percentiles,
    calculate_rolling_stats,
    calculate_deviation_from_mean,
    calculate_skewness,
    calculate_kurtosis,
    calculate_bollinger_bands,
    detect_volatility_squeeze_series,
    calculate_volume_analysis_series,
    find_pivot_levels_series,
    detect_consolidation_series,
    detect_breakout_setup_series,
    find_price_clusters,
    find_price_clusters_series,
    detect_volatility_squeeze,
    calculate_volume_analysis,
    detect_consolidation,
    detect_breakout_setup
)



# =============================================================================
# УПРАВЛЕНИЕ НАСТРОЙКАМИ
# =============================================================================

def load_user_prefs():
    """Загрузка пользовательских настроек из файла"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"⚠️ Не удалось прочитать конфиг: {e}")
    return DEFAULT_PREFS_PAGE2.copy()


def save_user_prefs(prefs):
    """Сохранение пользовательских настроек в файл"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"❌ Не удалось сохранить настройки: {e}")


def on_change_factory(key, attr_name, transform=None):
    """Фабрика колбэков для безопасного обновления session_state"""

    def callback():
        value = st.session_state[key]
        if transform:
            value = transform(value)
        setattr(st.session_state, attr_name, value)

    return callback


# =============================================================================
# ИНИЦИАЛИЗАЦИЯ STREAMLIT
# =============================================================================

st.set_page_config(layout="wide", page_title="Статистический анализ")
st.title("📊 Статистический анализ отклонений")

st.markdown("""
**Что здесь можно:**
- 📈 Свечной график цены
- 📏 **Скользящие** отклонения от средней (σ и MAD по Талебу)
- 🎯 Z-оценка для поиска аномалий
- 📊 Процентили для понимания распределения
""")

# Инициализация настроек
if 'prefs_loaded' not in st.session_state:
    st.session_state.prefs = load_user_prefs()
    st.session_state.prefs_loaded = True

prefs = st.session_state.prefs

# =============================================================================
# SIDEBAR: НАСТРОЙКИ
# =============================================================================

with st.sidebar:
    st.header("⚙️ Настройки")

    # Подключение к БД
    if st.button("🔗 Подключиться к БД"):
        if 'engine' not in st.session_state:
            engine, tunnel = get_connection()
            if engine:
                st.session_state.engine = engine
                st.session_state.tunnel = tunnel
                st.success("✅ Подключено!")
            else:
                st.error("❌ Не удалось подключиться")
        else:
            st.info("✅ Уже подключено")

    if 'engine' not in st.session_state:
        st.stop()

    st.divider()

    # Тикер
    if 'stat_ticker' not in st.session_state:
        st.session_state.stat_ticker = prefs.get("tickers", "SBER").split(',')[0].strip()

    stat_ticker = st.text_input(
        "Тикер для анализа",
        value=st.session_state.stat_ticker,
        key="stat_ticker_input",
        on_change=on_change_factory("stat_ticker_input", "stat_ticker", str.upper)
    ).upper()
    st.session_state.stat_ticker = stat_ticker

    # Таймфрейм
    if 'timeframe_input' not in st.session_state:
        st.session_state.timeframe_input = prefs["timeframe"]

    timeframe_options = ["1m", "5m", "1h", "1d"]
    current_idx = timeframe_options.index(
        st.session_state.timeframe_input) if st.session_state.timeframe_input in timeframe_options else 3

    timeframe_input = st.selectbox(
        "Таймфрейм",
        timeframe_options,
        index=current_idx,
        key="timeframe_box",
        on_change=on_change_factory("timeframe_box", "timeframe_input")
    )
    st.session_state.timeframe_input = timeframe_input

    # Даты
    if 'days_back_input' not in st.session_state:
        st.session_state.days_back_input = prefs.get("days_back", 30)

    col1, col2 = st.columns(2)
    with col1:
        default_start = datetime.date.today() - datetime.timedelta(days=st.session_state.days_back_input)
        start_date = st.date_input("📅 Начало", value=default_start, key="start_date_input")
    with col2:
        end_date = st.date_input("📅 Конец", value=datetime.date.today(), key="end_date_input")

    st.session_state.days_back_input = (datetime.date.today() - start_date).days

    # Тип цены
    if 'price_type_input' not in st.session_state:
        st.session_state.price_type_input = prefs["price_type"]

    price_options = ["Close", "(Low+High)/2", "(Low+High+Close)/3", "(Low+High+Close+Open)/4"]
    current_price_idx = price_options.index(
        st.session_state.price_type_input) if st.session_state.price_type_input in price_options else 0

    price_type_input = st.selectbox(
        "Тип цены",
        price_options,
        index=current_price_idx,
        key="price_type_box",
        on_change=on_change_factory("price_type_box", "price_type_input")
    )
    st.session_state.price_type_input = price_type_input

    st.divider()
    st.subheader("📏 Параметры отклонений")

    rolling_window = st.number_input(
        "Окно скользящей статистики (периодов)",
        min_value=5, max_value=200, value=20,
        help="Средняя и отклонения считаются по последним N периодам"
    )

    deviation_method = st.radio(
        "Метод расчёта отклонений",
        ["std", "mad"],
        format_func=lambda x: "Стандартное (σ)" if x == "std" else "По Талебу (MAD)",
        help="MAD более устойчив к выбросам"
    )

    show_z_score = st.checkbox("📊 Показать Z-оценку", value=True)
    show_percentiles = st.checkbox("📈 Показать процентили", value=True)
    show_skew_kurt = st.checkbox("📐 Показать скошенность и эксцесс", value=False)

    st.divider()
    st.subheader("🔍 Пробои и Консолидации")

    show_volume = st.checkbox("📦 Объём + OBV", value=False)
    show_consolidation = st.checkbox("🔄 Зоны консолидации", value=False)
    show_breakout = st.checkbox("🚀 Сигналы пробоя", value=False)
    show_levels = st.checkbox("📏 Уровни поддержки/сопротивления", value=False)
    show_clusters = st.checkbox("🎯 Ценовые кластеры (Volume Profile)", value=False)

    n_clusters = st.number_input(
        "Количество кластеров",
        min_value=3, max_value=15, value=5,
        disabled=not show_clusters,
        help="Сколько ценовых уровней найти"
    )

    load_btn = st.button("▶️ Построить анализ", type="primary")

    # Сохранение настроек при нажатии
    if load_btn:
        current_prefs = {
            "tickers": stat_ticker,
            "timeframe": timeframe_input,
            "price_type": price_type_input,
            "days_back": st.session_state.days_back_input,
            "rolling_window": rolling_window,
            "deviation_method": deviation_method,
            "show_z_score": show_z_score,
            "show_percentiles": show_percentiles
        }
        save_user_prefs(current_prefs)
        st.session_state.prefs = current_prefs


# =============================================================================
# ОСНОВНАЯ ЛОГИКА АНАЛИЗА
# =============================================================================

def prepare_data(engine, ticker, timeframe, start, end, price_type, window, method):
    """Подготовка и расчёт базовой статистики"""
    df_raw = fetch_candles(engine, [ticker], timeframe, start, end)

    if df_raw.empty:
        return None, None

    df_raw = df_raw.reset_index(drop=True)
    df_raw['price'] = calculate_price_type(df_raw, price_type)

    df_stats = calculate_deviation_from_mean(
        df_raw, price_col='price', window=window, method=method
    )

    return df_raw, df_stats


def calculate_indicators(df_raw, window, show_flags):
    """Расчёт дополнительных индикаторов по флагам"""
    results = {}

    if show_flags.get('breakout'):
        results['squeeze'] = detect_volatility_squeeze_series(df_raw['price'], window=window)
        results['consolidation'] = detect_consolidation_series(df_raw, window=window)
        results['breakout'] = detect_breakout_setup_series(df_raw, 'price', window=window)

    if show_flags.get('volume'):
        results['volume'] = calculate_volume_analysis_series(df_raw, 'price', window=window)

    if show_flags.get('consolidation') and 'consolidation' not in results:
        results['consolidation'] = detect_consolidation_series(df_raw, window=window)

    if show_flags.get('levels'):
        results['levels'] = find_pivot_levels_series(df_raw['price'], window=5)

    if show_flags.get('clusters'):
        results['clusters'] = find_price_clusters(df_raw['price'], n_clusters=show_flags.get('n_clusters', 5))

    return results


def build_price_chart(df_raw, df_stats, ticker, window, method, indicators, show_flags):
    """Построение основного графика цены"""
    fig = go.Figure()

    # Свечи
    fig.add_trace(go.Candlestick(
        x=df_raw['time'], open=df_raw['open'], high=df_raw['high'],
        low=df_raw['low'], close=df_raw['close'], name='Цена',
        increasing_line_color='green', decreasing_line_color='red',
        increasing_fillcolor='rgba(0, 255, 0, 0.3)',
        decreasing_fillcolor='rgba(255, 0, 0, 0.3)'
    ))

    # Линии отклонений
    method_prefix = 'stat_'
    colors = ['yellow', 'orange', 'red'] if method == 'std' else ['cyan', 'magenta', 'white']
    suffix = 'σ' if method == 'std' else 'MAD'

    for i, (label, color) in enumerate(zip(['±1', '±2', '±3'], colors), 1):
        pos_key, neg_key = f'stat_+{i}{suffix}', f'stat_-{i}{suffix}'
        fig.add_trace(go.Scatter(
            x=df_stats['time'], y=df_stats[pos_key],
            name=f'{label}{suffix} верх', line=dict(color=color, width=1.5, dash='dash'),
            opacity=0.5, showlegend=True
        ))
        fig.add_trace(go.Scatter(
            x=df_stats['time'], y=df_stats[neg_key],
            name=f'{label}{suffix} низ', line=dict(color=color, width=1.5, dash='dash'),
            opacity=0.5, fill='tonexty', fillcolor='rgba(255, 255, 255, 0.03)',
            showlegend=False
        ))

    # Скользящая средняя
    fig.add_trace(go.Scatter(
        x=df_stats['time'], y=df_stats[f'{method_prefix}mean'],
        name=f'SMA ({window})', line=dict(color='white', width=2, dash='dot'), opacity=0.8
    ))

    # ✅ ИСПРАВЛЕНО: Уровни поддержки/сопротивления
    if show_flags.get('levels') and indicators.get('levels') is not None:
        levels = indicators['levels']

        # Сопротивление (используем levels для y, df_raw для x)
        if 'is_high' in levels.columns and levels['is_high'].any() and 'resistance' in levels.columns:
            mask = levels['is_high']
            fig.add_trace(go.Scatter(
                x=df_raw.loc[mask, 'time'],
                y=levels.loc[mask, 'resistance'],  # ✅ Берём из levels, а не из df_raw
                name='Сопротивление', mode='markers',
                marker=dict(symbol='triangle-down', size=12, color='red'), showlegend=True
            ))

        # Поддержка
        if 'is_low' in levels.columns and levels['is_low'].any() and 'support' in levels.columns:
            mask = levels['is_low']
            fig.add_trace(go.Scatter(
                x=df_raw.loc[mask, 'time'],
                y=levels.loc[mask, 'support'],  # ✅ Берём из levels, а не из df_raw
                name='Поддержка', mode='markers',
                marker=dict(symbol='triangle-up', size=12, color='green'), showlegend=True
            ))

    # Зоны консолидации
    if show_flags.get('consolidation') and indicators.get('consolidation') is not None:
        consol = indicators['consolidation']
        if 'is_consolidation' in consol.columns and consol['is_consolidation'].any():
            mask = consol['is_consolidation']
            fig.add_vrect(
                x0=df_raw.loc[mask, 'time'].min(), x1=df_raw.loc[mask, 'time'].max(),
                fillcolor="yellow", opacity=0.15, layer="below", line_width=0,
                annotation_text="Консолидация", annotation_position="top left"
            )

    # Сигналы пробоя
    if show_flags.get('breakout') and indicators.get('breakout') is not None:
        breakout = indicators['breakout']
        if 'breakout_ready' in breakout.columns and breakout['breakout_ready'].any():
            mask = breakout['breakout_ready']
            fig.add_trace(go.Scatter(
                x=df_raw.loc[mask, 'time'], y=df_raw.loc[mask, 'close'],
                name='🚀 Пробой!', mode='markers',
                marker=dict(symbol='star', size=15, color='gold'), showlegend=True
            ))

    # Ценовые кластеры
    if show_flags.get('clusters') and indicators.get('clusters') is not None:
        clusters = indicators['clusters']
        for idx, (level, count) in enumerate(zip(clusters['levels'], clusters['counts'])):
            is_poc = (level == clusters['strongest_level'])
            fig.add_hline(
                y=level,
                line_color='gold' if is_poc else 'purple',
                line_width=3 if is_poc else 2,
                line_dash='solid' if is_poc else 'dash',
                opacity=0.7,
                annotation_text=f'{"🎯 POC" if is_poc else f"Кластер {idx + 1}"} ({count} свечей)',
                annotation_position='right'
            )

    fig.update_layout(
        title=f"💹 {ticker} | Отклонения: {window}п, {'σ' if method == 'std' else 'MAD'}",
        xaxis_title="Время", yaxis_title="Цена", height=600,
        template="plotly_dark", xaxis_rangeslider_visible=False,
        plot_bgcolor='rgba(0,0,0,0.8)', paper_bgcolor='rgba(0,0,0,0.8)'
    )

    return fig


def build_z_score_chart(df_stats, window):
    """Построение графика Z-оценки"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_stats['time'], y=df_stats['z_score'], name='Z-оценка',
        line=dict(color='cyan', width=2), fill='tozeroy',
        fillcolor='rgba(0, 255, 255, 0.2)'
    ))

    for y, color, dash in [(0, 'white', 'solid'), (2, 'yellow', 'dash'), (3, 'red', 'dash')]:
        fig.add_hline(y=y, line_color=color, line_width=1, line_dash=dash)
        fig.add_hline(y=-y, line_color=color, line_width=1, line_dash=dash)

    fig.update_layout(
        title=f"📊 Z-оценка (окно {window})",
        xaxis_title="Время", yaxis_title="Z", height=300, template="plotly_dark"
    )
    return fig


def build_volume_chart(df_raw, volume_data):
    """Построение графика объёмов"""
    fig = go.Figure()
    colors = ['green' if r > 1.5 else 'gray' for r in volume_data['volume_ratio']]

    fig.add_trace(go.Bar(
        x=df_raw['time'], y=volume_data['volume'], name='Объём',
        marker_color=colors, opacity=0.7
    ))
    fig.add_trace(go.Scatter(
        x=df_raw['time'], y=volume_data['avg_volume'], name='Средний',
        line=dict(color='yellow', width=2, dash='dash')
    ))

    fig.update_layout(
        title="📦 Объём (зелёный = спайк >150%)",
        height=300, template="plotly_dark", showlegend=True
    )
    return fig


def build_obv_chart(df_raw, volume_data):
    """Построение графика OBV"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_raw['time'], y=volume_data['obv'], name='OBV',
        line=dict(color='purple', width=2)
    ))

    if volume_data['accumulation'].any():
        mask = volume_data['accumulation']
        fig.add_trace(go.Scatter(
            x=df_raw[mask]['time'], y=volume_data['obv'][mask],
            name='✅ Накопление', mode='markers',
            marker=dict(symbol='circle', size=10, color='green'), showlegend=True
        ))

    fig.update_layout(
        title="📈 On-Balance Volume", height=300, template="plotly_dark"
    )
    return fig


def build_squeeze_chart(df_raw, breakout_data):
    """Построение графика сжатия волатильности"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_raw['time'], y=breakout_data['squeeze_strength'],
        name='Сила сжатия', line=dict(color='orange', width=2),
        fill='tozeroy', fillcolor='rgba(255, 165, 0, 0.3)'
    ))
    fig.add_hline(y=70, line_color='red', line_width=2, line_dash='dash',
                  annotation_text='🎯 Готов к пробою')

    fig.update_layout(
        title="🔧 Сжатие волатильности (0-100)",
        xaxis_title="Время", yaxis_title="Сила", height=300, template="plotly_dark"
    )
    return fig


def build_adx_chart(df_raw, consolidation_data):
    """Построение графика ADX"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_raw['time'], y=consolidation_data['adx'], name='ADX',
        line=dict(color='blue', width=2)
    ))
    fig.add_hline(y=25, line_color='yellow', line_width=2, line_dash='dash',
                  annotation_text='📊 Тренд/Флэт')

    fig.update_layout(
        title="📉 ADX (<25 = флэт)",
        xaxis_title="Время", yaxis_title="ADX", height=300, template="plotly_dark"
    )
    return fig


def render_skewness_kurtosis(df_raw, df_stats, window):
    """Расчёт и отображение скошенности и эксцесса"""
    # ✅ ИСПРАВЛЕНИЕ: считаем здесь, чтобы колонки существовали
    df_stats['skewness'] = calculate_skewness(df_raw['price'], window=window).values
    df_stats['kurtosis'] = calculate_kurtosis(df_raw['price'], window=window).values

    #col1, col2 = st.columns(2)

    #with col1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_stats['time'], y=df_stats['skewness'], name='Skewness',
        line=dict(color='purple', width=2)
    ))
    fig.add_hline(y=0, line_color='white', line_width=1)
    fig.update_layout(
        title="📐 Скошенность", yaxis_title="Значение",
        height=300, template="plotly_dark"
    )
    st.plotly_chart(fig, width='stretch')
    st.caption("**> 0** — правый хвост, **< 0** — левый хвост")

    #with col2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_stats['time'], y=df_stats['kurtosis'], name='Kurtosis',
        line=dict(color='orange', width=2)
    ))
    fig.add_hline(y=0, line_color='yellow', line_width=1, line_dash='dash',
                  annotation_text='Норма')
    fig.update_layout(
        title="📊 Эксцесс (Fisher)", yaxis_title="Значение",
        height=300, template="plotly_dark"
    )
    st.plotly_chart(fig, width='stretch')
    st.caption("**> 0** — тяжёлые хвосты ⚠️, **< 0** — лёгкие хвосты")

    return df_stats  # Возвращаем с добавленными колонками


def render_stats_table(df_raw, df_stats, show_skew_kurt):
    """Отображение итоговой таблицы статистики"""
    prices = df_raw['price']

    stats_rows = [
        ('Средняя (скользящая, тек.)', f"{df_stats['stat_mean'].iloc[-1]:.2f}"),
        ('Средняя (глобальная)', f"{prices.mean():.2f}"),
        ('Медиана', f"{prices.median():.2f}"),
        ('Мин', f"{prices.min():.2f}"),
        ('Макс', f"{prices.max():.2f}"),
        ('Текущая цена', f"{prices.iloc[-1]:.2f}"),
        ('Текущий Z-score', f"{df_stats['z_score'].iloc[-1]:.2f}"),
    ]

    # ✅ ИСПРАВЛЕНИЕ: добавляем skewness/kurtosis только если они рассчитаны
    if show_skew_kurt and 'skewness' in df_stats.columns and 'kurtosis' in df_stats.columns:
        stats_rows.extend([
            ('Скошенность', f"{df_stats['skewness'].iloc[-1]:.2f}"),
            ('Эксцесс (Fisher)', f"{df_stats['kurtosis'].iloc[-1]:.2f}"),
        ])

    df_stats_table = pd.DataFrame(stats_rows, columns=['Метрика', 'Значение'])
    st.dataframe(df_stats_table, width='stretch')


# =============================================================================
# ЗАПУСК АНАЛИЗА
# =============================================================================

if load_btn:
    with st.spinner('🔄 Считаем статистику...'):
        # Подготовка данных
        df_raw, df_stats = prepare_data(
            st.session_state.engine, stat_ticker, timeframe_input,
            start_date, end_date, price_type_input, rolling_window, deviation_method
        )

        if df_raw is None or df_stats is None:
            st.warning("⚠️ Нет данных. Проверьте тикер и даты.")
            st.stop()

        # Расчёт индикаторов
        show_flags = {
            'breakout': show_breakout,
            'volume': show_volume,
            'consolidation': show_consolidation,
            'levels': show_levels,
            'clusters': show_clusters,
            'n_clusters': n_clusters
        }
        indicators = calculate_indicators(df_raw, rolling_window, show_flags)

        # === ГРАФИК - Цена ===
        fig_price = build_price_chart(
            df_raw, df_stats, stat_ticker, rolling_window,
            deviation_method, indicators, show_flags
        )
        st.plotly_chart(fig_price, width='stretch')

        # === ГРАФИК - Объём ===
        if show_volume:
            if indicators.get('volume') is not None:
                vol_data = indicators['volume']
                st.plotly_chart(build_volume_chart(df_raw, vol_data), width='stretch')
                st.plotly_chart(build_obv_chart(df_raw, vol_data), width='stretch')
            else:
                st.warning("⚠️ Нет данных по объёму для этого тикера")

        # === ГРАФИК - Z-оценка ===
        if show_z_score:
            st.plotly_chart(build_z_score_chart(df_stats, rolling_window), width='stretch')

        # === Скошенность и эксцесс ===
        if show_skew_kurt:
            st.subheader(f"📐 Скошенность и эксцесс (окно {rolling_window})")
            df_stats = render_skewness_kurtosis(df_raw, df_stats, rolling_window)

        # === Ценовые кластеры (инфо) ===
        if show_clusters and indicators.get('clusters'):
            clusters = indicators['clusters']
            st.info(f"""
            **📊 Ценовые кластеры:**
            - 🎯 POC: **{clusters['strongest_level']:.2f}**
            - Уровней: {len(clusters['levels'])}
            - Диапазон: {min(clusters['levels']):.2f} — {max(clusters['levels']):.2f}
            """)

            # Таблица кластеров
            cluster_df = pd.DataFrame({
                'Уровень': [f'{l:.2f}' for l in clusters['levels']],
                'Свечей': clusters['counts'],
                '%': (np.array(clusters['counts']) / sum(clusters['counts']) * 100).round(1),
                'Тип': ['🎯 POC' if l == clusters['strongest_level'] else 'Уровень'
                        for l in clusters['levels']]
            }).sort_values('Свечей', ascending=False)

            st.dataframe(
                cluster_df.style.highlight_max(subset=['Свечей'], color='gold'),
                width='stretch', height=300
            )
            st.caption("💡 Цена часто возвращается к POC после отклонений")



        # === ГРАФИК 4: Сжатие ===
        if show_breakout and indicators.get('breakout') is not None:
            bd = indicators['breakout']
            st.plotly_chart(build_squeeze_chart(df_raw, bd), width='stretch')

            # Метрики пробоя
            st.subheader("🚀 Сигналы пробоя")
            c1, c2, c3, c4 = st.columns(4)
            ready = bd['breakout_ready']
            last = bd[ready]

            with c1: st.metric("Сигналов", int(ready.sum()))
            with c2: st.metric("Последний", last.index[-1] if not last.empty else "Нет")
            with c3:
                direction = last['probable_direction'].iloc[-1] if not last.empty else "-"
                st.metric("Направление", direction)
            with c4:
                strength = last['squeeze_strength'].iloc[-1] if not last.empty else 0
                st.metric("Сила", f"{strength:.0f}%")

        # === ГРАФИК 5: ADX ===
        if show_consolidation and indicators.get('consolidation') is not None:
            st.plotly_chart(build_adx_chart(df_raw, indicators['consolidation']), width='stretch')

        # === Процентили ===
        if show_percentiles:
            st.subheader("📈 Процентили (глобальные)")
            perc = calculate_percentiles(df_raw['price'], [10, 25, 50, 75, 90])
            st.dataframe(
                pd.DataFrame({'Процентиль': list(perc.keys()), 'Цена': [f'{v:.2f}' for v in perc.values()]}),
                width='stretch'
            )

        # === Итоговая таблица ===
        st.subheader("📊 Сводная статистика")
        render_stats_table(df_raw, df_stats, show_skew_kurt)