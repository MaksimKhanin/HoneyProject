# Параметризация метрик (period, window)

## Обзор

Все метрики теперь поддерживают параметризацию через `period` и `window`. Это позволяет:
- Использовать одну и ту же метрику с разными параметрами
- Избегать дублирования кода
- Динамически создавать метрики под конкретные задачи

## Изменения

### 1. Базовый класс `PandasMetric`

Добавлен конструктор с параметрами:

```python
class PandasMetric(BaseMetric):
    default_period: int = 14
    default_window: int = 20

    def __init__(self, period: Optional[int] = None, window: Optional[int] = None):
        self.period = period if period is not None else self.default_period
        self.window = window if window is not None else self.default_window
```

### 2. Шаблон имени метрики

Имя метрики может содержать плейсхолдеры `{period}` и `{window}`:

```python
class RSIMetric(PandasMetric):
    name = "rsi_{period}"  # Будет заменено на rsi_14, rsi_21 и т.д.
    description = "RSI — индикатор перекупленности/перепроданности"
    default_period = 14
```

### 3. Реестр метрик

Функция `get_metric()` теперь поддерживает параметры:

```python
# Получить метрику с параметрами по умолчанию
rsi = get_metric("rsi_{period}")  # period=14

# Получить метрику с кастомным периодом
rsi_21 = get_metric("rsi_{period}", period=21)

# Получить метрику по имени с числом
rsi_14 = get_metric("rsi_14")  # Автоматически создаст RSI(period=14)

# Pullback с кастомным окном
pullback = get_metric("pullback_{window}", window=30)
```

## Примеры использования

### RSI с разными периодами

```python
from docker.data_loader.metrics.registry import get_metric

# RSI(14) - по умолчанию
rsi_14 = get_metric("rsi_14")
result = rsi_14.calculate('BTC', '1h', candles)

# RSI(21) - кастомный период
rsi_21 = get_metric("rsi_{period}", period=21)
result = rsi_21.calculate('BTC', '1h', candles)

# RSI(7) - короткий период
rsi_7 = get_metric("rsi_{period}", period=7)
result = rsi_7.calculate('BTC', '1h', candles)
```

### EMA с разными периодами

```python
# EMA(50) - по умолчанию
ema_50 = get_metric("ema_{period}")
result = ema_50.calculate('BTC', '1h', candles)

# EMA(20) - короткий период
ema_20 = get_metric("ema_{period}", period=20)
result = ema_20.calculate('BTC', '1h', candles)

# EMA(200) - длинный период
ema_200 = get_metric("ema_{period}", period=200)
result = ema_200.calculate('BTC', '1h', candles)
```

### Pullback с разными окнами

```python
# Pullback(20) - по умолчанию
pb_20 = get_metric("pullback_{window}")
result = pb_20.calculate('BTC', '1h', candles)

# Pullback(50) - большее окно
pb_50 = get_metric("pullback_{window}", window=50)
result = pb_50.calculate('BTC', '1h', candles)
```

## Список доступных параметризованных метрик

| Метрика | Плейсхолдер | По умолчанию | Описание |
|---------|-------------|--------------|----------|
| `rsi_{period}` | period | 14 | RSI индикатор |
| `ema_{period}` | period | 50 | Экспоненциальная скользящая средняя |
| `pullback_{window}` | window | 20 | Откат от максимума |
| `z_score_{period}` | period | 200 | Z-score цены |
| `price_change_pct_{period}` | period | 3 | Изменение цены в % |
| `skew_kurt_{period}` | period | 200 | Асимметрия и эксцесс |
| `close_price` | - | - | Цена закрытия (без параметров) |

## Создание своей параметризованной метрики

```python
from docker.data_loader.metrics.base import PandasMetric
from docker.data_loader.metrics.registry import register_metric
from typing import Dict, Any

@register_metric
class MyCustomMetric(PandasMetric):
    """Моя кастомная метрика с параметром."""
    name = "my_metric_{period}"  # Шаблон имени
    description = "Описание метрики"
    default_period = 10  # Значение по умолчанию
    
    @property
    def min_candles(self) -> int:
        return self.period * 2  # Используем self.period
    
    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        # Используем self.period в расчётах
        closes = df['close'].iloc[-self.min_candles:]
        result = closes.rolling(window=self.period).mean().iloc[-1]
        return {f"my_metric_{self.period}": round(result, 4)}
```

### Использование:

```python
# Метрика с period=10 (по умолчанию)
metric_default = get_metric("my_metric_{period}")

# Метрика с period=20
metric_20 = get_metric("my_metric_{period}", period=20)

# Или по имени
metric_10 = get_metric("my_metric_10")
```

## Миграция старых метрик

Если у вас есть код, который использует старые имена метрик:

```python
# Старый код (работает как прежде)
rsi = get_metric("rsi_14")  # Автоматически создаст RSI(period=14)

# Новый код (более гибкий)
rsi = get_metric("rsi_{period}", period=14)  # Явное указание периода
```

Реестр автоматически распознаёт оба формата.

## Преимущества

1. **Гибкость**: Одна метрика → множество конфигураций
2. **DRY**: Нет дублирования кода для разных периодов
3. **Совместимость**: Старые имена метрик продолжают работать
4. **Производительность**: pandas-реализация быстрее pure Python в 10-100 раз
5. **Консистентность**: Одинаковое поведение в backtesting и production
