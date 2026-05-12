# pages/03_📋_Сводная_таблица.py
import streamlit as st
import pandas as pd
import numpy as np
import datetime
import json
from pathlib import Path

from core.database import get_connection, get_all_tickers, get_latest_candle
from core.stats import (
    generate_trading_signal,
    calculate_price_type,
    detect_volatility_squeeze_series,
    detect_breakout_setup_series
)


# =============================================================================
# УПРАВЛЕНИЕ НАСТРОЙКАМИ
# =============================================================================

CONFIG_FILE = Path("page3_summary_config.json")


def load_user_prefs():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Не удалось прочитать конфиг: {e}")
    return {
        "timeframe": "1d",
        "window": 20,
        "price_type": "Close",
        "min_confidence": 50,
        "max_days_old": 5
    }


def save_user_prefs(prefs):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Не смог сохранить настройки: {e}")


# =============================================================================
# UI
# =============================================================================

st.set_page_config(layout="wide", page_title="Сводная таблица")
st.title("📋 Сводная таблица торговых сигналов")

st.info("""
**💡 Совет:** При увеличении окна анализа меньше тикеров проходят проверку на достаточность данных.
Если видишь мало инструментов — уменьши окно или проверь базу на наличие исторических данных.
""")

st.markdown("""
**Агрегированный обзор всех инструментов в базе**

- 🔄 Автоматическая проверка актуальности данных (не старше N дней)
- 📊 Все статистические метрики в одной таблице
- 🎯 Цветовое выделение экстремумов и асимметрии
- ⚡ Быстрый скрининг возможностей
""")

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

    # Таймфрейм
    if 'timeframe_input' not in st.session_state:
        st.session_state.timeframe_input = prefs.get("timeframe", "1d")

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

    # Окно анализа
    if 'window_input' not in st.session_state:
        st.session_state.window_input = prefs.get("window", 20)

    window_input = st.number_input(
        "Окно анализа (периодов)",
        min_value=5,
        max_value=100,
        value=st.session_state.window_input,
        key="window_num",
        on_change=lambda: setattr(st.session_state, 'window_input', st.session_state.window_num)
    )
    st.session_state.window_input = window_input

    # Тип цены
    if 'price_type_input' not in st.session_state:
        st.session_state.price_type_input = prefs.get("price_type", "Close")

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
    st.subheader("Фильтры")

    # Максимальная давность данных
    if 'max_days_old' not in st.session_state:
        st.session_state.max_days_old = prefs.get("max_days_old", 5)

    max_days_old = st.number_input(
        "Макс. давность данных (дней)",
        min_value=1,
        max_value=30,
        value=st.session_state.max_days_old,
        key="days_num",
        on_change=lambda: setattr(st.session_state, 'max_days_old', st.session_state.days_num)
    )
    st.session_state.max_days_old = max_days_old

    st.divider()

    load_btn = st.button("Обновить таблицу", type="primary")

    if load_btn:
        current_prefs = {
            "timeframe": timeframe_input,
            "window": window_input,
            "price_type": price_type_input,
            "max_days_old": max_days_old
        }
        save_user_prefs(current_prefs)
        st.session_state.prefs = current_prefs


# =============================================================================
# ОСНОВНАЯ ЛОГИКА
# =============================================================================

if load_btn:
    with st.spinner('Сканируем рынок, не суетись...'):
        engine = st.session_state.engine

        # 1. Получаем все тикеры
        df_tickers = get_all_tickers(engine, max_days_old=max_days_old)

        if df_tickers.empty:
            st.error("Нет тикеров в базе или данные устарели!")
            st.stop()

        # Фильтруем по таймфрейму
        df_tickers_tf = df_tickers[df_tickers['timeframe'] == timeframe_input]

        if df_tickers_tf.empty:
            st.warning(f"Нет данных по таймфрейму {timeframe_input}")
            st.stop()

        total_tickers = len(df_tickers_tf)
        st.info(f"Найдено {total_tickers} инструментов по таймфрейму {timeframe_input}")

        # 2. Считаем метрики для каждого тикера
        results = []
        skipped_tickers = []

        progress_bar = st.progress(0)
        status_text = st.empty()

        for counter, (_, row) in enumerate(df_tickers_tf.iterrows()):
            ticker = row['ticker']
            last_update = row['last_update']

            status_text.text(f"Обработка {ticker}... ({counter + 1}/{total_tickers})")

            # Загружаем с запасом (window + 50%)
            load_window = int(window_input * 1.5) + 10
            df_candles = get_latest_candle(engine, ticker, timeframe_input, window=load_window)

            # Проверка на наличие данных
            if df_candles.empty:
                skipped_tickers.append({'ticker': ticker, 'reason': 'Нет данных'})
                results.append({
                    'Ticker': ticker,
                    'Last Update': last_update,
                    'Price': np.nan,
                    'Z-Score': np.nan,
                    'Skewness': np.nan,
                    'Kurtosis': np.nan,
                    'Squeeze Strength': np.nan,
                    'Reason': 'Нет данных в базе'  # ✅ Reason ПОСЛЕДНИЙ
                })
                progress_bar.progress((counter + 1) / total_tickers)
                continue

            if len(df_candles) < window_input:
                skipped_tickers.append({
                    'ticker': ticker,
                    'reason': f'Мало свечей ({len(df_candles)} < {window_input})'
                })
                results.append({
                    'Ticker': ticker,
                    'Last Update': last_update,
                    'Price': round(df_candles['close'].iloc[-1], 2) if 'close' in df_candles.columns else np.nan,
                    'Z-Score': np.nan,
                    'Skewness': np.nan,
                    'Kurtosis': np.nan,
                    'Squeeze Strength': np.nan,
                    'Reason': f'Недостаточно данных ({len(df_candles)}/{window_input})'  # ✅ Reason ПОСЛЕДНИЙ
                })
                progress_bar.progress((counter + 1) / total_tickers)
                continue

            # Считаем цену
            df_candles['price'] = calculate_price_type(df_candles, price_type_input)

            # Генерируем сигнал (нужен только для поля Reason)
            signal = generate_trading_signal(df_candles['price'], window=window_input)

            # =================================================================
            # 👇 НОВЫЕ МЕТРИКИ: Squeeze Strength
            # =================================================================

            min_required = window_input + 20
            squeeze_strength = np.nan

            if len(df_candles) >= min_required:
                try:
                    squeeze_series = detect_volatility_squeeze_series(
                        df_candles['price'],
                        window=window_input
                    )
                    if squeeze_series is not None and not squeeze_series.empty:
                        last_squeeze = squeeze_series.iloc[-1]
                        squeeze_strength = last_squeeze.get('squeeze_strength', np.nan)
                except:
                    pass  # тихий фолбэк

            # ✅ Формируем результат — Reason ПОСЛЕДНИЙ
            results.append({
                'Ticker': ticker,
                'Last Update': last_update.strftime('%Y-%m-%d %H:%M'),
                'Price': round(df_candles['price'].iloc[-1], 2),
                'Z-Score': signal['z_score'],
                'Skewness': signal['skewness'],
                'Kurtosis': signal['kurtosis'],
                'Squeeze Strength': round(squeeze_strength, 1) if pd.notna(squeeze_strength) else np.nan,
                'Reason': signal['reason']  # ✅ Reason ПОСЛЕДНИЙ
            })

            progress_bar.progress((counter + 1) / total_tickers)

        progress_bar.empty()
        status_text.empty()

        # ✅ Показываем статистику по пропущенным
        if skipped_tickers:
            st.warning(f"⚠️ Пропущено тикеров: {len(skipped_tickers)} из {total_tickers}")
            with st.expander(f"Показать пропущенные тикеры ({len(skipped_tickers)})"):
                skipped_df = pd.DataFrame(skipped_tickers)
                st.dataframe(skipped_df, use_container_width=True)

        # 3. Создаём DataFrame
        df_results = pd.DataFrame(results)

        # ✅ Явно задаём порядок колонок: Reason — последний
        column_order = [
            'Ticker',
            'Last Update',
            'Price',
            'Z-Score',
            'Skewness',
            'Kurtosis',
            'Squeeze Strength',
            'Reason'  # ✅ Последняя колонка
        ]
        # Применяем порядок только для существующих колонок
        column_order = [c for c in column_order if c in df_results.columns]
        df_results = df_results[column_order]

        # 4. Сортируем по абсолютному Z-Score (экстремумы в приоритете)
        df_results['Z-Score Abs'] = df_results['Z-Score'].abs()
        df_results = df_results.sort_values('Z-Score Abs', ascending=False)
        df_results = df_results.drop(columns=['Z-Score Abs'])

        # =====================================================================
        # ОТОБРАЖЕНИЕ
        # =====================================================================

        # Метрики
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Всего инструментов", total_tickers)
        with col2:
            extremes = len(df_results[(df_results['Z-Score'].abs() > 2) & (df_results['Z-Score'].notna())])
            st.metric("Экстремумы (|Z|>2)", extremes)
        with col3:
            dangerous = len(df_results[(df_results['Kurtosis'] > 3) & (df_results['Kurtosis'].notna())])
            st.metric("Опасные (Kurt>3)", dangerous)
        with col4:
            squeezes = len(df_results[(df_results['Squeeze Strength'] >= 70) & (df_results['Squeeze Strength'].notna())])
            st.metric("Сжатия (Squeeze≥70)", squeezes)

        st.divider()

        # Таблица
        st.subheader("📊 Торговые сигналы")

        # =================================================================
        # Функции раскраски
        # =================================================================

        def color_z_score(val):
            if pd.isna(val):
                return ''
            if val < -3:
                return 'background-color: #006400; color: white; font-weight: bold'
            elif val < -2:
                return 'background-color: #228B22; color: white'
            elif val > 3:
                return 'background-color: #8B0000; color: white; font-weight: bold'
            elif val > 2:
                return 'background-color: #DC143C; color: white'
            return ''

        def color_kurtosis(val):
            if pd.isna(val):
                return ''
            if val > 3:
                return 'background-color: #8B0000; color: white; font-weight: bold'
            elif val > 0:
                return 'background-color: #FFA500; color: black'
            elif val < -0.5:
                return 'background-color: #228B22; color: white'
            return ''

        def color_skewness(val):
            """✅ Раскраска Skewness: 🔴 <= -1, 🟢 >= 1"""
            if pd.isna(val):
                return ''
            if val <= -1:
                return 'background-color: #8B0000; color: white; font-weight: bold'
            elif val >= 1:
                return 'background-color: #228B22; color: white; font-weight: bold'
            return ''

        def color_squeeze_strength(val):
            """Раскраска Squeeze Strength: чем выше — тем краснее (сильнее сжатие)"""
            if pd.isna(val):
                return ''
            if val >= 80:
                return 'background-color: #8B0000; color: white; font-weight: bold'
            elif val >= 60:
                return 'background-color: #DC143C; color: white'
            elif val >= 40:
                return 'background-color: #FFA500; color: black'
            return ''

        # Применяем стили
        styled_df = df_results.style \
            .applymap(color_z_score, subset=['Z-Score']) \
            .applymap(color_kurtosis, subset=['Kurtosis']) \
            .applymap(color_skewness, subset=['Skewness']) \
            .applymap(color_squeeze_strength, subset=['Squeeze Strength'])

        # ✅ Перенос текста в колонке Reason
        if 'Reason' in df_results.columns:
            styled_df = styled_df.set_properties(
                subset=['Reason'],
                **{
                    "white-space": "normal",
                    "word-wrap": "break-word",
                    "overflow-wrap": "break-word",
                    "max-width": "300px",
                    "min-width": "150px"
                }
            )

        # ✅ Скрываем индекс (левый столбец с номерами)
        styled_df = styled_df.hide(axis="index")

        # Показываем таблицу
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=600,
            hide_index=True
        )

        # =====================================================================
        # ЭКСПОРТ
        # =====================================================================
        st.divider()
        st.subheader("💾 Экспорт")

        csv = df_results.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="Скачать CSV",
            data=csv,
            file_name=f"trading_signals_{timeframe_input}_{datetime.date.today()}.csv",
            mime="text/csv"
        )

        # =====================================================================
        # 🔥 Топ по экстремальным отклонениям
        # =====================================================================
        st.divider()
        st.subheader("🔥 Топ экстремумов")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🟢 Самые низкие (потенциал роста)")
            low_z = df_results[(df_results['Z-Score'] < -2) & (df_results['Z-Score'].notna())].nsmallest(5, 'Z-Score')
            if not low_z.empty:
                for _, row in low_z.iterrows():
                    st.success(f"**{row['Ticker']}** — Z: {row['Z-Score']}, Skew: {row['Skewness']}")
                    st.caption(row['Reason'])
            else:
                st.info("Нет выраженных минимумов")

        with col2:
            st.markdown("### 🔴 Самые высокие (потенциал падения)")
            high_z = df_results[(df_results['Z-Score'] > 2) & (df_results['Z-Score'].notna())].nlargest(5, 'Z-Score')
            if not high_z.empty:
                for _, row in high_z.iterrows():
                    st.error(f"**{row['Ticker']}** — Z: {row['Z-Score']}, Skew: {row['Skewness']}")
                    st.caption(row['Reason'])
            else:
                st.info("Нет выраженных максимумов")