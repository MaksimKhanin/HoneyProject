import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from sshtunnel import SSHTunnelForwarder
import datetime
import json
from pathlib import Path

# =============================================================================
# --- КОНФИГУРАЦИЯ ---
# =============================================================================

# Данные для доступа к серверу (лучше вынести в .streamlit/secrets.toml)
SSH_HOST = st.secrets["ssh"]["host"] #'212.87.222.132'
SSH_USER = st.secrets["ssh"]["user"] #'khanin'
SSH_PORT = 22
SSH_KEY_FILE = r'C:\Users\Khanin Maksim\.ssh\id_ed25519'  # Если по ключу — раскомментируй

DB_USER = st.secrets["db"]["user"] #'khanin'
DB_PASS = st.secrets["db"]["pass"] #'qaZXsw21Aa!'
DB_NAME = st.secrets["db"]["name"] #'trade_db'
DB_PORT = 5432

# Файл для сохранения настроек (лежит рядом со скриптом)
CONFIG_FILE = Path("last_run_config.json")


# =============================================================================
# --- ФУНКЦИИ ---
# =============================================================================

def load_user_prefs():
    """Грузим прошлые настройки из файла, если он есть"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Не удалось прочитать конфиг: {e}")
    # Дефолтные значения, если файла нет
    return {
        "tickers": "SBER, TCSG, BR",
        "timeframe": "1d",
        "price_type": "Close",
        "benchmarks": "",
        "apply_factor": False,
        "days_back": 30
    }


def save_user_prefs(prefs):
    """Сохраняем текущие настройки в файл"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Не смог сохранить настройки: {e}")


@st.cache_resource
def get_connection():
    """Поднимает SSH туннель и возвращает коннект к БД"""
    try:
        tunnel = SSHTunnelForwarder(
            (SSH_HOST, SSH_PORT),
            ssh_username=SSH_USER,
            ssh_pkey=SSH_KEY_FILE,  # Если по ключу — раскомментируй эту строку
            #ssh_password='qaZXsw21Aa!',
            remote_bind_address=('127.0.0.1', DB_PORT)
        )
        tunnel.start()

        conn_str = f"postgresql://{DB_USER}:{DB_PASS}@127.0.0.1:{tunnel.local_bind_port}/{DB_NAME}"
        engine = create_engine(conn_str)
        return engine, tunnel
    except Exception as e:
        st.error(f"Не удалось подключиться к серверу, чёрт возьми! Ошибка: {e}")
        return None, None


def fetch_candles(engine, tickers, timeframe, start_date, end_date):
    """Грузим свечи из базы"""
    if not tickers:
        return pd.DataFrame()

    start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
    end_datetime = datetime.datetime.combine(end_date, datetime.time.max)

    placeholders = ','.join(['%s'] * len(tickers))

    query = f"""
        SELECT ticker, time, open, high, low, close 
        FROM tink.candles 
        WHERE ticker IN ({placeholders}) 
        AND timeframe = %s 
        AND time BETWEEN %s AND %s
        ORDER BY ticker, time
    """

    params = tuple(tickers) + (timeframe, start_datetime, end_datetime)

    try:
        df = pd.read_sql(query, engine, params=params)
        return df
    except Exception as e:
        st.error(f"Ошибка при загрузке данных: {e}")
        return pd.DataFrame()


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
# --- UI ИНТЕРФЕЙС ---
# =============================================================================

st.set_page_config(layout="wide", page_title="Trader UI")
st.title("📈 Аналитика и Факторный Анализ")

# !!! ИСПРАВЛЕНИЕ: Загружаем настройки ТОЛЬКО при первом запуске !!!
if 'prefs_loaded' not in st.session_state:
    st.session_state.prefs = load_user_prefs()
    st.session_state.prefs_loaded = True

# Берём настройки из session_state, а не из файла напрямую
prefs = st.session_state.prefs

# Сайдбар с настройками
with st.sidebar:
    st.header("Настройки")

    # Подключение
    st.subheader("Коннект")
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

    # Выбор данных — используем session_state для сохранения между ререндерами
    if 'tickers_input' not in st.session_state:
        st.session_state.tickers_input = prefs["tickers"]

    tickers_input = st.text_area(
        "Тикеры (через запятую)",
        value=st.session_state.tickers_input,
        key="tickers_area",
        on_change=lambda: setattr(st.session_state, 'tickers_input', st.session_state.tickers_area),
        help="Пример: SBER, TCSG, YNDX"
    )
    # Синхронизируем session_state с текущим значением
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
        st.session_state.days_back_input = prefs.get("days_back", 30)

    col1, col2 = st.columns(2)
    with col1:
        default_start = datetime.date.today() - datetime.timedelta(days=st.session_state.days_back_input)
        start_date = st.date_input("Начало", value=default_start, key="start_date_input")
    with col2:
        end_date = st.date_input("Конец", value=datetime.date.today(), key="end_date_input")

    # Обновляем days_back при изменении даты
    st.session_state.days_back_input = (datetime.date.today() - start_date).days

    # Тип цены
    if 'price_type_input' not in st.session_state:
        st.session_state.price_type_input = prefs["price_type"]

    price_options = [
        "Close",
        "(Low+High)/2",
        "(Low+High+Close)/3",
        "(Low+High+Close+Open)/4"
    ]
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

    if 'benchmarks_input' not in st.session_state:
        st.session_state.benchmarks_input = prefs["benchmarks"]

    benchmarks_input = st.text_input(
        "Бенчмарки (через запятую)",
        value=st.session_state.benchmarks_input,
        key="benchmarks_field",
        on_change=lambda: setattr(st.session_state, 'benchmarks_input', st.session_state.benchmarks_field)
    )
    st.session_state.benchmarks_input = benchmarks_input
    benchmark_list = [t.strip().upper() for t in benchmarks_input.split(',') if t.strip()]

    if 'apply_factor_input' not in st.session_state:
        st.session_state.apply_factor_input = prefs.get("apply_factor", False)

    apply_factor_input = st.checkbox(
        "Вычесть среднее бенчмарков",
        value=st.session_state.apply_factor_input,
        key="apply_factor_chk",
        on_change=lambda: setattr(st.session_state, 'apply_factor_input', st.session_state.apply_factor_chk)
    )
    st.session_state.apply_factor_input = apply_factor_input

    load_btn = st.button("Построить график", type="primary")

    # Сохраняем настройки в файл ТОЛЬКО при нажатии кнопки
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
        # Обновляем session_state prefs для следующих запусков
        st.session_state.prefs = current_prefs

# =============================================================================
# --- ОСНОВНАЯ ЛОГИКА ---
# =============================================================================

if load_btn:
    with st.spinner('Грузим данные, не суетись...'):
        # 1. Грузим сырые данные
        df_raw = fetch_candles(st.session_state.engine, ticker_list, timeframe_input, start_date, end_date)

        if df_raw.empty:
            st.warning("Данных нет. Проверь тикеры и даты.")
            st.stop()

        # 2. Считаем нужную цену
        df_raw['price'] = calculate_price_type(df_raw, price_type_input)

        # 3. Нормализуем к 100% на старте
        df_norm = normalize_returns(df_raw)

        # 4. Факторный анализ (вычитание бенчмарков)
        if apply_factor_input and benchmark_list:
            valid_benches = [b for b in benchmark_list if b in ticker_list]
            if not valid_benches:
                st.error(f"Ни один из бенчмарков {benchmark_list} не в списке тикеров! Добавь их.")
                st.stop()
            df_norm = subtract_benchmark(df_norm, valid_benches)
            st.info(f"Режим относительной силы относительно {valid_benches}")

        # 5. Строим график
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

        # Таблица с итогами
        st.subheader("Итоговая доходность за период")
        summary = df_norm.groupby('ticker')['norm_price'].last().reset_index()
        summary.columns = ['Ticker', 'Finish Value']
        summary['Return %'] = (summary['Finish Value'] - 100).round(2)
        st.dataframe(summary.style.highlight_max(axis=0, subset=['Return %'], color='green'))