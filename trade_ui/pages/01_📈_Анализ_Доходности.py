# pages/01_📈_Анализ_Доходности.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
import json
from pathlib import Path

from core.config import CONFIG_FILE_PAGE1 as CONFIG_FILE, DEFAULT_PREFS
from core.database import get_connection, fetch_candles
from core.stats import calculate_price_type, normalize_returns, subtract_benchmark


# =============================================================================
# УПРАВЛЕНИЕ НАСТРОЙКАМИ
# =============================================================================

def load_user_prefs():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Не удалось прочитать конфиг: {e}")
    return DEFAULT_PREFS.copy()

def save_user_prefs(prefs):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Не смог сохранить настройки: {e}")

# =============================================================================
# UI
# =============================================================================

st.set_page_config(layout="wide", page_title="Анализ доходности")
st.title("📈 Анализ доходности")

if 'prefs_loaded' not in st.session_state:
    st.session_state.prefs = load_user_prefs()
    st.session_state.prefs_loaded = True

prefs = st.session_state.prefs

with st.sidebar:
    st.header("Настройки")

    if st.button("Подключиться к БД"):
        if 'engine' not in st.session_state:
            engine, tunnel = get_connection()
            if engine:
                st.session_state.engine = engine
                st.session_state.tunnel = tunnel
                st.success("Подключено!")
            else:
                st.error("Не удалось подключиться")
        else:
            st.info("Уже подключено")

    if 'engine' not in st.session_state:
        st.stop()

    st.divider()

    # Тикеры
    if 'tickers_input' not in st.session_state:
        st.session_state.tickers_input = prefs["tickers"]

    tickers_input = st.text_area(
        "Тикеры (через запятую)",
        value=st.session_state.tickers_input,
        key="tickers_area",
        on_change=lambda: setattr(st.session_state, 'tickers_input', st.session_state.tickers_area)
    )
    st.session_state.tickers_input = tickers_input
    ticker_list = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]

    # Таймфрейм
    if 'timeframe_input' not in st.session_state:
        st.session_state.timeframe_input = prefs["timeframe"]

    timeframe_options = ["1m", "5m", "1h", "1d"]
    timeframe_input = st.selectbox(
        "Таймфрейм",
        timeframe_options,
        index=timeframe_options.index(
            st.session_state.timeframe_input) if st.session_state.timeframe_input in timeframe_options else 3,
        key="timeframe_box",
        on_change=lambda: setattr(st.session_state, 'timeframe_input', st.session_state.timeframe_box)
    )
    st.session_state.timeframe_input = timeframe_input

    # Даты
    if 'days_back_input' not in st.session_state:
        st.session_state.days_back_input = prefs.get("days_back", 30)  # ✅ Правильно

    col1, col2 = st.columns(2)
    with col1:
        default_start = datetime.date.today() - datetime.timedelta(days=st.session_state.days_back_input)
        start_date = st.date_input("Начало", value=default_start, key="start_date_input")
    with col2:
        end_date = st.date_input("Конец", value=datetime.date.today(), key="end_date_input")

    st.session_state.days_back_input = (datetime.date.today() - start_date).days

    # Тип цены
    if 'price_type_input' not in st.session_state:
        st.session_state.price_type_input = prefs.get("price_type", "Close")  # ✅ Добавь .get()

    price_options = ["Close", "(Low+High)/2", "(Low+High+Close)/3", "(Low+High+Close+Open)/4"]
    price_type_input = st.selectbox(
        "Тип цены",
        price_options,
        index=price_options.index(
            st.session_state.price_type_input) if st.session_state.price_type_input in price_options else 0,
        key="price_type_box",
        on_change=lambda: setattr(st.session_state, 'price_type_input', st.session_state.price_type_box)
    )
    st.session_state.price_type_input = price_type_input

    st.divider()
    st.subheader("Бенчмарки")

    # ✅ ИСПРАВЛЕНИЕ: используем .get() с дефолтом!
    if 'benchmarks_input' not in st.session_state:
        st.session_state.benchmarks_input = prefs.get("benchmarks", "")  # ✅ БЫЛО prefs["benchmarks"]

    benchmarks_input = st.text_input(
        "Бенчмарки (через запятую)",
        value=st.session_state.benchmarks_input,
        key="benchmarks_field",
        on_change=lambda: setattr(st.session_state, 'benchmarks_input', st.session_state.benchmarks_field)
    )
    st.session_state.benchmarks_input = benchmarks_input
    benchmark_list = [t.strip().upper() for t in benchmarks_input.split(',') if t.strip()]

    # ✅ ИСПРАВЛЕНИЕ: используем .get() с дефолтом!
    if 'apply_factor_input' not in st.session_state:
        st.session_state.apply_factor_input = prefs.get("apply_factor",
                                                        False)  # ✅ БЫЛО prefs.get("apply_factor", False) - тут было правильно

    apply_factor_input = st.checkbox(
        "Вычесть среднее бенчмарков",
        value=st.session_state.apply_factor_input,
        key="apply_factor_chk",
        on_change=lambda: setattr(st.session_state, 'apply_factor_input', st.session_state.apply_factor_chk)
    )
    st.session_state.apply_factor_input = apply_factor_input

    load_btn = st.button("Построить график", type="primary")

    if load_btn:
        current_prefs = {
            "tickers": tickers_input,
            "timeframe": timeframe_input,
            "price_type": price_type_input,
            "benchmarks": benchmarks_input,
            "apply_factor": apply_factor_input,
            "days_back": st.session_state.days_back_input
        }
        save_user_prefs(current_prefs)
        st.session_state.prefs = current_prefs

# =============================================================================
# ОСНОВНАЯ ЛОГИКА
# =============================================================================

if load_btn:
    with st.spinner('Грузим данные, не суетись...'):
        df_raw = fetch_candles(st.session_state.engine, ticker_list, timeframe_input, start_date, end_date)

        if df_raw.empty:
            st.warning("Данных нет. Проверь тикеры и даты.")
            st.stop()

        df_raw['price'] = calculate_price_type(df_raw, price_type_input)
        df_norm = normalize_returns(df_raw)

        if apply_factor_input and benchmark_list:
            valid_benches = [b for b in benchmark_list if b in ticker_list]
            if not valid_benches:
                st.error(f"Ни один из бенчмарков {benchmark_list} не в списке тикеров! Добавь их.")
                st.stop()
            df_norm = subtract_benchmark(df_norm, valid_benches)
            st.info(f"Режим относительной силы относительно {valid_benches}")

        fig = go.Figure()
        for ticker in df_norm['ticker'].unique():
            df_ticker = df_norm[df_norm['ticker'] == ticker]
            is_bench = ticker in benchmark_list if benchmark_list else False

            fig.add_trace(go.Scatter(
                x=df_ticker['time'],
                y=df_ticker['norm_price'],
                name=ticker,
                mode='lines',
                line=dict(width=4 if is_bench else 2)
            ))

        fig.update_layout(
            title=f"Доходность инструментов ({price_type_input})",
            xaxis_title="Время",
            yaxis_title="Доходность (база 100%)",
            hovermode='x unified',
            height=600,
            template="plotly_dark"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Итоговая доходность за период")
        summary = df_norm.groupby('ticker')['norm_price'].last().reset_index()
        summary.columns = ['Ticker', 'Finish Value']
        summary['Return %'] = (summary['Finish Value'] - 100).round(2)
        st.dataframe(summary.style.highlight_max(axis=0, subset=['Return %'], color='green'))