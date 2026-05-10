# test_bt_adapter.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtesting import Backtest
from strategies.trailing_trend import TrailingTrendStrategy
#from adapters.backtesting import BTAdapter
from adapters.backtesting import create_bt_adapter

# 1. Генерируем синтетический df с метриками (эмуляция твоего df2)
dates = pd.date_range("2021-01-01", periods=100, freq="h")
df = pd.DataFrame({
    "Open": np.linspace(300, 350, 100) + np.random.randn(100)*2,
    "High": np.linspace(302, 352, 100) + np.random.randn(100)*2,
    "Low":  np.linspace(298, 348, 100) + np.random.randn(100)*2,
    "Close": np.linspace(301, 351, 100) + np.random.randn(100)*2,
    "Volume": np.random.randint(10000, 50000, 100),
    # Метрики, которые ожидает стратегия
    "ema_50": np.linspace(290, 340, 100),
    "pullback_20": np.full(100, 0.04),  # всегда > 0.03, чтобы пропускать вход
    "kurt_excess_200": np.full(100, 1.0),
    "skew_200": np.full(100, 0.2)
}, index=dates)

df = df.dropna()  # backtesting не любит NaN

# 2. Инициализируем ядро стратегии
core = TrailingTrendStrategy(
    params={"min_pullback": 0.03, "hard_stop": 0.08, "TSL": 0.05, "cooldown_sec": 3600},
    direction="BUY_ONLY"
)



bt = Backtest(df, create_bt_adapter(core), cash=100_000, commission=0.0015, trade_on_close=True)
stats = bt.run()

print("✅ Бэктест прошёл без ошибок")
print(f"📊 Прибыльность: {stats['Return [%]']:.2f}%")
print(f"📈 Сделок: {stats['# Trades']}")
print("🎉 Адаптер backtesting.py работает корректно.")