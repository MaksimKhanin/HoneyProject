# Миграция метрик на pandas

## Обзор изменений

Все метрики переписаны с pure Python на **pandas** для:
- ✅ Совместимости с `backtesting.py` (библиотека использует pandas)
- ✅ Производительности (векторизированные операции быстрее в 10-100 раз)
- ✅ Устранения багов при переходе между тестированием и production

## Изменения в архитектуре

### 1. Новый базовый класс `PandasMetric`

```python
from metrics.base import PandasMetric

class MyMetric(PandasMetric):
    name = "my_metric"
    description = "Описание метрики"
    
    def calculate_pandas(self, df, **kwargs) -> Dict[str, Any]:
        # df - это pandas DataFrame с колонками: open, high, low, close, volume
        result = df['close'].mean()
        return {"my_metric": result}
```

### 2. Старый класс `PythonMetric` сохранён для обратной совместимости

```python
from metrics.base import PythonMetric  # legacy, не рекомендуется

class LegacyMetric(PythonMetric):
    def calculate_python(self, candles: List[Dict], **kwargs) -> Dict[str, Any]:
        # candles - список словарей (pure Python)
        pass
```

## API `PandasMetric`

### Входные данные

Метод `calculate_pandas()` получает:
- `df: pd.DataFrame` - DataFrame со свечами
  - Колонки: `open`, `high`, `low`, `close`, `volume`, `time`
  - Индекс: integer (0, 1, 2, ...)
- `**kwargs` - дополнительные параметры (ticker, timeframe, etc.)

### Примеры использования pandas операций

```python
# Скользящее среднее
sma = df['close'].rolling(window=20).mean()

# EMA
ema = df['close'].ewm(span=50, adjust=False).mean()

# RSI
delta = df['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rsi = 100 - (100 / (1 + gain / loss))

# Лог-доходности
log_rets = df['close'].pct_change().apply(lambda x: math.log(1 + x))

# Статистика
mean = log_rets.mean()
std = log_rets.std(ddof=0)  # population std
skew = ((log_rets - mean) ** 3).mean() / (log_rets.var() ** 1.5)
kurt = ((log_rets - mean) ** 4).mean() / (log_rets.var() ** 2) - 3

# Максимум за период
max_close = df['close'].iloc[-20:].max()
```

## Обновлённые метрики

| Метрика | Описание | Период |
|---------|----------|--------|
| `rsi_14` | RSI индикатор | 14 |
| `ema_50` | Экспоненциальная скользящая средняя | 50 |
| `pullback_20` | Откат от максимума | 20 |
| `z_score_200` | Z-score лог-доходностей | 200 |
| `skew_kurt_200` | Асимметрия и эксцесс | 200 |
| `price_change_pct_3` | Изменение цены в % | 3 |
| `close_price` | Цена закрытия | 1 |

## Требования

В `requirements.txt` добавлены:
```
pandas>=2.0.0
numpy>=1.24.0
```

## Тестирование

```python
import sys
sys.path.insert(0, '/workspace/docker/data_loader')

from metrics.builtins.python_metrics import RSIMetric, EMA50Metric

# Тестовые данные
candles = [
    {'time': ..., 'open': 100, 'high': 101, 'low': 99, 'close': 100.5, 'volume': 1000},
    ...
]

# Расчёт метрики
rsi = RSIMetric()
result = rsi.calculate("BTC/USD", "1h", candles)
print(result)  # {'rsi_14': 52.34}
```

## Преимущества миграции

1. **Единая кодовая база**: Одинаковый код для backtesting и production
2. **Производительность**: Векторизированные операции pandas быстрее циклов Python
3. **Надёжность**: Меньше багов из-за различий в реализации
4. **Читаемость**: Код на pandas короче и понятнее

## Обратная совместимость

- Старые метрики на `PythonMetric` продолжают работать
- SQL-метрики без изменений
- API `MetricsEngine` не изменился
