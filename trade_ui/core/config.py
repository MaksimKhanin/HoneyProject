# core/config.py
import streamlit as st
from pathlib import Path

# Раздельные конфиги для каждой страницы
CONFIG_FILE_HOME = Path("last_run_config.json")  # Общие настройки
CONFIG_FILE_PAGE1 = Path("page1_income_config.json")  # Анализ доходности
CONFIG_FILE_PAGE2 = Path("page2_stats_config.json")   # Статистический анализ

# Настройки по умолчанию
DEFAULT_PREFS = {
    "tickers": "SBER, TCSG, BR",
    "timeframe": "1d",
    "price_type": "Close",
    "benchmarks": "",
    "apply_factor": False,
    "days_back": 30
}

DEFAULT_PREFS_PAGE2 = {
    "tickers": "SBER",
    "timeframe": "1d",
    "price_type": "Close",
    "days_back": 30,
    "rolling_window": 20,
    "deviation_method": "std",
    "show_z_score": True,
    "show_percentiles": True
}

def get_db_config():
    """Возвращает конфиг для подключения к БД"""
    return {
        "ssh_host": st.secrets["ssh"]["host"],
        "ssh_user": st.secrets["ssh"]["user"],
        "ssh_port": 22,
        "ssh_key": r'C:\Users\Khanin Maksim\.ssh\id_ed25519',
        "db_user": st.secrets["db"]["user"],
        "db_pass": st.secrets["db"]["pass"],
        "db_name": st.secrets["db"]["name"],
        "db_port": 5432
    }