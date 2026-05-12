# test_core.py
from datetime import datetime
from cvstrategy import Bar, Signal, BaseStrategy
from metrics_joiner import MetricsJoiner

# Тест 1: Bar создаётся
bar = Bar(
    time=datetime.now(),
    open=100, high=102, low=99, close=101, volume=1000,
    metrics={"ema_50": 100.5, "pullback_20": 0.02}
)
assert bar.close == 101
assert bar.metrics["ema_50"] == 100.5
print("✅ Test 1: Bar OK")

# Тест 2: Signal — строки
assert Signal.BUY == "BUY"
assert Signal.HOLD.value == "HOLD"
print("✅ Test 2: Signal OK")

# Тест 3: MetricsJoiner.join
candles = [
    {"time": datetime(2024, 1, 1, 10), "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 100},
    {"time": datetime(2024, 1, 1, 11), "open": 100.5, "high": 102, "low": 100, "close": 101.5, "volume": 120},
]
metrics = [
    {"time": datetime(2024, 1, 1, 10), "metrics": {"ema_50": 100.2}},
    {"time": datetime(2024, 1, 1, 11), "metrics": {"ema_50": 100.8}},
]
bars = MetricsJoiner.join(candles, metrics)
assert len(bars) == 2
assert bars[0].metrics["ema_50"] == 100.2
assert bars[1].close == 101.5
print("✅ Test 3: MetricsJoiner OK")

print("\n🎉 Все тесты прошли. Фундамент готов.")