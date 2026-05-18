# strategies/trend_hunter.py
from strategy.strategy_core import BaseStrategy, Bar, Signal
from typing import Dict, Optional, Any


class TrendHunterStrategy(BaseStrategy):
    """
    TrendHunter Strategy - Адаптация backtesting стратегии под проект.

    Логика:
    - Вход по пересечению EMA + Z-score фильтр + объёмный фильтр
    - Трейлинг с режимом momentum на основе Z-score
    - Выход при развороте momentum или противоположном сигнале
    """
    name = "TrendHunter"

    _params_schema = {
        "period_slow": {
            "type": "int", "default": 60, "min": 10, "max": 200,
            "desc": "Период медленной EMA"
        },
        "period_fast": {
            "type": "int", "default": 27, "min": 5, "max": 100,
            "desc": "Период быстрой EMA"
        },
        "vol_ratio_lvl": {
            "type": "float", "default": 2.0, "min": 0.5, "max": 5.0,
            "desc": "Уровень фильтра объёма (коэффициент)"
        },
        "cooldown_bars": {
            "type": "int", "default": 5, "min": 1, "max": 100,
            "desc": "Кулдаун после выхода (в барах)"
        },
        "risk_prcnt": {
            "type": "float", "default": 0.1, "min": 0.01, "max": 0.5,
            "desc": "Максимальный риск на сделку (% от цены)"
        },
        "z_score_entry_min": {
            "type": "float", "default": 1.0, "min": 0.5, "max": 3.0,
            "desc": "Минимальный Z-score для входа в лонг"
        },
        "z_score_entry_max": {
            "type": "float", "default": 2.0, "min": 1.0, "max": 4.0,
            "desc": "Максимальный Z-score для входа в лонг"
        },
        "z_score_momentum": {
            "type": "float", "default": 2.0, "min": 1.0, "max": 4.0,
            "desc": "Порог Z-score для включения momentum режима"
        },
        "direction": {
            "type": "select", "default": "ALL",
            "options": ["BUY_ONLY", "SHORT_ONLY", "ALL"],
            "desc": "Направление торговли"
        },
    }

    def __init__(self, params: Optional[Dict] = None, direction: str = "ALL", log_level: str = None):
        super().__init__(params, direction, log_level)

        # 🔥 Инициализация параметров
        self.period_slow = self.params.get("period_slow", 60)
        self.period_fast = self.params.get("period_fast", 27)
        self.vol_ratio_lvl = self.params.get("vol_ratio_lvl", 2.0)
        self.cooldown_bars = self.params.get("cooldown_bars", 5)
        self.risk_prcnt = self.params.get("risk_prcnt", 0.1)
        self.z_score_entry_min = self.params.get("z_score_entry_min", 1.0)
        self.z_score_entry_max = self.params.get("z_score_entry_max", 2.0)
        self.z_score_momentum = self.params.get("z_score_momentum", 2.0)

        # 🔥 Счётчик баров после выхода
        self.bars_since_exit = 100

        # 🔥 Состояние трейлинга
        self.trailing_mode = False
        self.momentum_flg = False

    def on_bar(self, bar: Bar) -> Signal:
        self._bar_count += 1
        self.bars_since_exit += 1

        # 🔥 Если не в позиции и кулдаун не истёк → HOLD
        if not self.in_position and self.bars_since_exit < self.cooldown_bars:
            return Signal.PASS

        if not self.in_position:
            return self._try_enter(bar)

        return self._manage_position(bar)

    def _try_enter(self, bar: Bar) -> Signal:
        # Чтение метрик (онлайн-расчёт через _get_metric если нет в БД)
        ema_slow = self._get_metric(bar, f"ema_{self.period_slow}", 0)
        ema_fast = self._get_metric(bar, f"ema_{self.period_fast}", 0)
        z_score = self._get_metric(bar, f"z_score_{self.period_slow}", 0)
        vol_ratio = self._get_metric(bar, f"vol_ratio_{self.period_fast}", 1.0)
        mov_min = self._get_metric(bar, f"mov_min_{self.period_fast}", bar.low)
        mov_max = self._get_metric(bar, f"mov_max_{self.period_fast}", bar.high)

        # 🔹 Проверка входа в LONG
        if self._can_enter_long():
            # Условия: EMA fast > EMA slow, Z-score в диапазоне, объёмный фильтр
            if ema_fast > ema_slow and \
               self.z_score_entry_min < z_score < self.z_score_entry_max and \
               vol_ratio > 1.0 + (self.vol_ratio_lvl / 10.0):

                # Проверка стоп-лосса
                sl = mov_min
                if sl < bar.close:
                    risk = 1 - (sl / bar.close)
                    if risk <= self.risk_prcnt:
                        self.in_position = True
                        self.position_type = "long"
                        self.entry_price = bar.close
                        self.current_sl = sl
                        self.trailing_mode = False
                        self.momentum_flg = False
                        return Signal.BUY

        # 🔹 Проверка входа в SHORT
        if self._can_enter_short():
            # Условия: EMA fast < EMA slow, Z-score в отрицательном диапазоне, объёмный фильтр
            # Оригинальное условие: ema_slow[-1] > ema_fast[-1] and z_score[-1]<-1 and z_score[-1]>-2
            if ema_fast < ema_slow and \
               -self.z_score_entry_max < z_score < -self.z_score_entry_min and \
               vol_ratio < 1.0 - (self.vol_ratio_lvl / 10.0):

                # Проверка стоп-лосса
                sl = mov_max
                if sl > bar.close:
                    risk = (sl / bar.close) - 1
                    if risk <= self.risk_prcnt:
                        self.in_position = True
                        self.position_type = "short"
                        self.entry_price = bar.close
                        self.current_sl = sl
                        self.trailing_mode = False
                        self.momentum_flg = False
                        return Signal.SELL

        return Signal.PASS

    def _manage_position(self, bar: Bar) -> Signal:
        # 🔥 Восстановление SL после синхронизации/рестарта
        if self.in_position and self.current_sl == 0:
            if self.position_type == "long":
                self.current_sl = self.entry_price * (1 - self.risk_prcnt)
            else:
                self.current_sl = self.entry_price * (1 + self.risk_prcnt)

        # Чтение метрик (онлайн-расчёт через _get_metric если нет в БД)
        z_score = self._get_metric(bar, f"z_score_{self.period_slow}", 0)
        mov_min = self._get_metric(bar, f"mov_min_{self.period_fast}", bar.low)
        mov_max = self._get_metric(bar, f"mov_max_{self.period_fast}", bar.high)

        if self.position_type == "long":
            # 🔥 Активация трейлинг режима (цена превысила предыдущий максимум)
            # Используем bar.high для сравнения, т.к. mov_max включает текущий бар
            if bar.high > mov_max or bar.close > mov_max:
                self.trailing_mode = True

            # 🔥 Momentum логика
            if self.trailing_mode:
                if z_score > self.z_score_momentum and not self.momentum_flg:
                    self.momentum_flg = True

                if self.momentum_flg:
                    if z_score < 0:
                        self._close_position(bar)
                        self.bars_since_exit = 0
                        return Signal.CLOSE_BUY

            # 🔥 Выход по противоположному сигналу
            ema_slow = self._get_metric(bar, f"ema_{self.period_slow}", 0)
            ema_fast = self._get_metric(bar, f"ema_{self.period_fast}", 0)

            if ema_fast <= ema_slow and z_score <= -self.z_score_entry_min:
                self._close_position(bar)
                self.bars_since_exit = 0
                return Signal.CLOSE_BUY

            # 🔥 Выход по стоп-лоссу
            if bar.close < self.current_sl:
                self._close_position(bar)
                self.bars_since_exit = 0
                return Signal.CLOSE_BUY

        elif self.position_type == "short":
            # 🔥 Активация трейлинг режима (цена пробила предыдущий минимум)
            if bar.low < mov_min or bar.close < mov_min:
                self.trailing_mode = True

            # 🔥 Momentum логика
            if self.trailing_mode:
                if z_score < -self.z_score_momentum and not self.momentum_flg:
                    self.momentum_flg = True

                if self.momentum_flg:
                    if z_score > 0:
                        self._close_position(bar)
                        self.bars_since_exit = 0
                        return Signal.CLOSE_SELL

            # 🔥 Выход по противоположному сигналу
            ema_slow = self._get_metric(bar, f"ema_{self.period_slow}", 0)
            ema_fast = self._get_metric(bar, f"ema_{self.period_fast}", 0)

            if ema_fast >= ema_slow and z_score >= self.z_score_entry_min:
                self._close_position(bar)
                self.bars_since_exit = 0
                return Signal.CLOSE_SELL

            # 🔥 Выход по стоп-лоссу
            if bar.close > self.current_sl:
                self._close_position(bar)
                self.bars_since_exit = 0
                return Signal.CLOSE_SELL

        return Signal.HOLD

    def _get_relevant_metrics(self, bar: Bar) -> Dict[str, Any]:
        """Возвращает только те метрики, которые реально используются в логике."""

        self.logger.info(f"🔍 _get_relevant_metrics вызван для {bar.time if bar else 'None'}")

        ctx = {
            f"EMA_{self.period_slow}": round(self._get_metric(bar, f"ema_{self.period_slow}", 0), 2),
            f"EMA_{self.period_fast}": round(self._get_metric(bar, f"ema_{self.period_fast}", 0), 2),
            f"Z-Score_{self.period_slow}": round(self._get_metric(bar, f"z_score_{self.period_slow}", 0), 2),
            f"VolRatio_{self.period_fast}": round(self._get_metric(bar, f"vol_ratio_{self.period_fast}", 1.0), 2),
            "TrailingMode": "ON" if self.trailing_mode else "OFF",
            "MomentumFlg": "YES" if self.momentum_flg else "NO",
            "Cooldown": f"{self.cooldown_bars - self.bars_since_exit} bars left" if not self.in_position else None
        }

        self.logger.info(f"_get_relevant_metrics returns  {ctx}")

        return ctx