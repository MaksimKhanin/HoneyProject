# strategies/trailing_trend.py
from strategy.strategy_core import BaseStrategy, Bar, Signal
from typing import Dict, Optional, Any


class TrailingTrendStrategy(BaseStrategy):
    name = "TrailingTrend"

    _params_schema = {
        "min_pullback": {
            "type": "float", "default": 0.03, "min": -1.0, "max": 0.5,
            "desc": "Мин. откат цены для входа (3% = 0.03)"
        },
        "hard_stop": {
            "type": "float", "default": 0.08, "min": 0.01, "max": 0.5,
            "desc": "Жёсткий стоп-лосс (% от входа)"
        },
        "TSL": {
            "type": "float", "default": 0.05, "min": 0.01, "max": 0.3,
            "desc": "Трейлинг-стоп: % от текущей цены для подтяжки"
        },
        "cooldown_bars": {
            "type": "int", "default": 7, "min": 1, "max": 100,
            "desc": "Кулдаун после выхода (в барах текущего таймфрейма)"
        },
        "max_kurt_excess": {
            "type": "float", "default": 3.0, "min": 0, "max": 10,
            "desc": "Макс. эксцесс для фильтра 'жирных хвостов' (Талеб-режим)"
        },
        "min_skew_for_long": {
            "type": "float", "default": -0.5, "min": -2.0, "max": 2.0,
            "desc": "Мин. скошенность для входа в лонг (фильтр левого хвоста)"
        },
        "direction": {
            "type": "select", "default": "ALL",
            "options": ["BUY_ONLY", "SHORT_ONLY", "ALL"],
            "desc": "Направление торговли"
        },
    }

    def __init__(self, params: Optional[Dict] = None, direction: str = "ALL"):
        super().__init__(params, direction)

        # 🔥 Инициализация параметров
        self.min_pullback = self.params.get("min_pullback", 0.03)
        self.hard_stop = self.params.get("hard_stop", 0.08)
        self.tsl_pct = self.params.get("TSL", 0.05)
        self.cooldown_bars = self.params.get("cooldown_bars", 7)  # 🔥 Теперь в барах
        self.max_kurt_excess = self.params.get("max_kurt_excess", 3.0)
        #self.min_skew_for_long = self.params.get("min_skew_for_long", -0.5)

        # 🔥 Счётчик баров после выхода
        self.bars_since_exit = 100

    def on_bar(self, bar: Bar) -> Signal:
        self._bar_count += 1
        self.bars_since_exit += 1  # 🔥 Увеличиваем счётчик на каждом баре

        # 🔥 Если не в позиции и кулдаун не истёк → HOLD
        if not self.in_position and self.bars_since_exit < self.cooldown_bars:
            return Signal.PASS

        if not self.in_position:
            # Фильтр жирных хвостов (раскомментируй, если нужен)
            # if self._get_metric(bar, "kurt_excess_200", 0) > self.max_kurt_excess:
            #     return Signal.HOLD
            return self._try_enter(bar)

        return self._manage_position(bar)

    def _try_enter(self, bar: Bar) -> Signal:
        pullback = self._get_metric(bar, "pullback_20", 1.0)
        ema50 = self._get_metric(bar, "ema_50", 0)
        #skew = self._get_metric(bar, "skew_200", 0)

        if self._can_enter_long():
            if pullback < self.min_pullback:      return Signal.PASS
            if bar.close <= ema50:                return Signal.PASS
            if bar.close <= bar.open:             return Signal.PASS
            #if skew < self.min_skew_for_long:     return Signal.HOLD

            self.in_position = True
            self.position_type = "long"
            self.entry_price = bar.close
            self.current_sl = bar.close * (1 - self.hard_stop)
            return Signal.BUY

        if self._can_enter_short():
            pass

        return Signal.PASS

    def _manage_position(self, bar: Bar) -> Signal:

        # 🔥 Восстановление SL после синхронизации/рестарта
        # Если позиция есть, но SL = 0 → значит, это первый бар после sync
        if self.in_position and self.current_sl == 0:
            self.current_sl = self.entry_price * (1 - self.hard_stop)


        pnl_pct = self._calc_pnl_pct(bar.close)

        if self.position_type == "long" and pnl_pct >= self.tsl_pct:
            new_sl = bar.close * (1 - self.tsl_pct)
            if new_sl > self.current_sl:
                self.current_sl = new_sl

        # 🚨 Выход по стопу
        if bar.close < self.current_sl:
            pos_type = self.position_type
            self._close_position(bar)
            self.bars_since_exit = 0  # 🔥 Сброс кулдауна при выходе
            return Signal.CLOSE_BUY if pos_type == "long" else Signal.CLOSE_SELL

        # 📉 Выход по EMA
        ema50 = self._get_metric(bar, "ema_50", 0)
        if self.position_type == "long" and bar.close < ema50:
            self._close_position(bar)
            self.bars_since_exit = 0  # 🔥 Сброс кулдауна при выходе
            return Signal.CLOSE_BUY

        return Signal.HOLD

    def _get_relevant_metrics(self, bar: Bar) -> Dict[str, Any]:
        """Возвращает только те метрики, которые реально используются в логике."""
        return {
            "EMA_50": round(self._get_metric(bar, "ema_50"), 2),
            "Pullback_20": f"{self._get_metric(bar, 'pullback_20') * 100:.2f}%",
            "Kurtosis_200": self._get_metric(bar, "kurt_excess_200", 0),
            "Skewness_200": self._get_metric(bar, "skew_200", 0),
            "Cooldown": f"{self.cooldown_bars - self.bars_since_exit} bars left" if not self.in_position else None
        }