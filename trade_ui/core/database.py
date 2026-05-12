# core/database.py
import streamlit as st
from sqlalchemy import create_engine, text
from sshtunnel import SSHTunnelForwarder
import pandas as pd
import datetime
from .config import get_db_config


@st.cache_resource
def get_connection():
    """Поднимает SSH туннель и возвращает коннект к БД"""
    cfg = get_db_config()
    try:
        tunnel = SSHTunnelForwarder(
            (cfg["ssh_host"], cfg["ssh_port"]),
            ssh_username=cfg["ssh_user"],
            ssh_pkey=cfg["ssh_key"],
            remote_bind_address=('127.0.0.1', cfg["db_port"])
        )
        tunnel.start()

        conn_str = f"postgresql://{cfg['db_user']}:{cfg['db_pass']}@127.0.0.1:{tunnel.local_bind_port}/{cfg['db_name']}"
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
        SELECT ticker, time, open, high, low, close, volume 
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


def get_all_tickers(engine, max_days_old=5):
    """
    Получаем все тикеры из базы с проверкой актуальности
    """
    query = """
        SELECT DISTINCT ticker, timeframe, MAX(time) as last_update, COUNT(*) as candle_count
        FROM tink.candles
        GROUP BY ticker, timeframe
        ORDER BY ticker, timeframe
    """

    try:
        df = pd.read_sql(query, engine)

        # Фильтруем по актуальности
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=max_days_old)
        df = df[df['last_update'] >= cutoff_date]

        return df
    except Exception as e:
        st.error(f"Ошибка при получении тикеров: {e}")
        return pd.DataFrame()


def get_latest_candle(engine, ticker, timeframe, window=30):
    """
    Получаем последние N свечей для тикера

    window: минимальное количество свечей (загружаем с запасом)
    """
    # Загружаем с запасом 50% на случай пропуска некоторых расчётов
    load_count = int(window * 1.5) + 10

    query = f"""
        SELECT ticker, time, open, high, low, close, volume
        FROM tink.candles
        WHERE ticker = %s AND timeframe = %s
        ORDER BY time DESC
        LIMIT %s
    """

    try:
        df = pd.read_sql(query, engine, params=(ticker, timeframe, load_count))

        if df.empty:
            return pd.DataFrame()

        # Разворачиваем чтобы время шло по возрастанию
        df = df.iloc[::-1].reset_index(drop=True)

        return df
    except Exception as e:
        st.error(f"Ошибка при загрузке свечей {ticker}: {e}")
        return pd.DataFrame()

