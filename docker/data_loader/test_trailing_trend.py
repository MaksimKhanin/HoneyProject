# test_trailing_trend.py
from datetime import datetime, timedelta
from strategy.strategy import Bar, Signal
from strategy.strategies.trailing_trend import TrailingTrendStrategy

def make_bar(dt, close, metrics=None):
    # Генерируем стандартную бычью свечу (open < close)
    return Bar(
        time=dt,
        open=round(close * 0.995, 2),
        high=round(close * 1.005, 2),
        low=round(close * 0.99, 2),
        close=close,
        volume=100000,
        metrics=metrics or {}
    )

strategy = TrailingTrendStrategy(
    params={
        "min_pullback": 0.03,
        "hard_stop": 0.08,
        "TSL": 0.05,
        "cooldown_sec": 3600,
        "max_kurt_excess": 3.0,
        "min_skew_for_long": -0.5
    },
    direction="BUY_ONLY"
)

# ==========================================================
# Тест 1: Вход
# ==========================================================
print("🧪 Тест 1: Вход по тренду + откату")
t0 = datetime(2024, 1, 1, 10)
entered = False
for i in range(5):
    bar = make_bar(t0 + timedelta(hours=i), close=310 + i, metrics={
        "ema_50": 300, "pullback_20": 0.04, "kurt_excess_200": 1.0, "skew_200": 0.2
    })
    sig = strategy.on_bar(bar)
    if sig == Signal.BUY:
        print(f"✅ Бар {i}: {sig.value} @ {bar.close} | SL={strategy.current_sl:.2f}")
        entered = True
        break
assert entered and strategy.in_position, "❌ Вход не сработал"

# ==========================================================
# Тест 2: Трейлинг-стоп + выход на падении
# ==========================================================
print("\n🧪 Тест 2: Трейлинг-стоп срабатывает на падении")
# Поднимаем цену, чтобы трейлинг подтянулся вверх
for i in range(5):
    price = 330 + i * 2
    bar = make_bar(t0 + timedelta(hours=6+i), close=price, metrics={
        "ema_50": 305, "pullback_20": 0.05, "kurt_excess_200": 1.0, "skew_200": 0.1
    })
    strategy.on_bar(bar)
    print(f"   Бар +{i+6}: close={price}, SL подтянут до {strategy.current_sl:.2f}")

# Резкое падение ниже текущего SL
drop_price = 310.0  # Гарантированно ниже любого подтянутого SL (>313)
drop_bar = make_bar(t0 + timedelta(hours=11), close=drop_price, metrics={
    "ema_50": 310, "pullback_20": 0.1, "kurt_excess_200": 1.0, "skew_200": 0.0
})
sig = strategy.on_bar(drop_bar)

print(f"   📉 Падение до {drop_price} | Текущий SL: {strategy.current_sl:.2f} | Сигнал: {sig.value}")
assert sig == Signal.CLOSE_BUY, f"❌ Ожидался CLOSE_BUY, получен {sig.value}"
assert not strategy.in_position, "❌ Позиция не закрылась"
print("✅ Тест 2 пройден")

# ==========================================================
# Тест 3: Фильтр жирных хвостов
# ==========================================================
print("\n🧪 Тест 3: Фильтр жирных хвостов блокирует вход")
strategy._reset_state()
fat_bar = make_bar(t0 + timedelta(hours=20), close=315, metrics={
    "ema_50": 300, "pullback_20": 0.04, "kurt_excess_200": 4.2, "skew_200": -0.8
})
assert strategy.on_bar(fat_bar) == Signal.HOLD
print("✅ Тест 3 пройден: kurt_excess > 3 → HOLD")

print("\n🎉 Все тесты TrailingTrend прошли. Стратегия готова.")