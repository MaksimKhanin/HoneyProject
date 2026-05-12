# adapters/backtesting.py
"""
Универсальный адаптер-фабрика для backtesting.py.
Возвращает класс, а не экземпляр, чтобы пройти проверку issubclass().
Автоматически подхватывает любые метрики из DataFrame.
"""
from typing import Type
import math
from datetime import datetime
from backtesting import Strategy as BTStrategy
from strategy.strategy_core import BaseStrategy, Bar, Signal


def create_bt_adapter(core_strategy: BaseStrategy) -> Type[BTStrategy]:
    """
    Фабрика: принимает настроенный экземпляр BaseStrategy,
    возвращает класс, совместимый с backtesting.py.
    """

    class _WrappedBTStrategy(BTStrategy):
        # Привязываем ядро стратегии к классу
        _core = core_strategy
        _RESERVED_COLS = {"Open", "High", "Low", "Close", "Volume"}

        def init(self):
            """Вызывается библиотекой перед стартом. super() НЕ трогаем."""
            pass

        def next(self):
            """Вызывается на каждом баре."""
            bar = Bar(
                time=self._extract_time(),
                open=float(self.data.Open[-1]),
                high=float(self.data.High[-1]),
                low=float(self.data.Low[-1]),
                close=float(self.data.Close[-1]),
                volume=float(self.data.Volume[-1]),
                metrics=self._extract_metrics_auto()
            )

            signal = self._core.on_bar(bar)
            self._execute_bt(signal)

        def _extract_time(self) -> datetime:
            ts = self.data.index[-1]
            if hasattr(ts, 'to_pydatetime'):
                return ts.to_pydatetime()
            return datetime.fromtimestamp(ts)

        def _extract_metrics_auto(self) -> dict:
            """
            Универсальный поиск метрик.
            Берёт ВСЕ колонки DataFrame, кроме стандартных OHLCV.
            Никакого хардкода.
            """
            metrics = {}
            # backtesting хранит исходный DataFrame в self.data._df
            if hasattr(self.data, '_df'):
                for col in self.data._df.columns:
                    if col in self._RESERVED_COLS:
                        continue
                    try:
                        val = float(getattr(self.data, col)[-1])
                        if not math.isnan(val):
                            metrics[col] = val
                    except (TypeError, ValueError, AttributeError):
                        pass
            return metrics

        def _execute_bt(self, signal: Signal):
            if signal == Signal.BUY:
                self.buy()
            elif signal == Signal.SELL:
                self.sell()
            elif signal in (Signal.CLOSE_BUY, Signal.CLOSE_SELL, Signal.CLOSE_ALL):
                if self.position:
                    self.position.close()

    return _WrappedBTStrategy