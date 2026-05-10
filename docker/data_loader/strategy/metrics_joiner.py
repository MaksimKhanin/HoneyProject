# metrics_joiner.py
"""
Утилита для склейки свечей и метрик из БД в объекты Bar.
Pure Python, no pandas.
"""
from datetime import datetime
from typing import List, Dict
from strategy.strategy_core import Bar


class MetricsJoiner:
    """
    Склейка: candles (List[Dict]) + metrics (List[Dict]) → List[Bar]

    Предполагает, что данные отсортированы по времени ASC (старые → новые).
    """

    @staticmethod
    def join(candles: List[Dict], metrics_list: List[Dict]) -> List[Bar]:
        """
        :param candles: [{'time': dt, 'open': ..., 'close': ...}, ...]
        :param metrics_list: [{'time': dt, 'metrics': {...}}, ...]
        :return: List[Bar] с подставленными метриками
        """
        if not candles:
            return []

        # Создаём словарь для быстрого поиска метрик по времени
        metrics_map = {}
        for m in metrics_list:
            # Нормализуем время к timestamp для надёжного сравнения
            ts = m['time'].timestamp() if isinstance(m['time'], datetime) else m['time']
            metrics_map[ts] = m.get('metrics', {}) or {}

        bars = []
        for c in candles:
            ts = c['time'].timestamp() if isinstance(c['time'], datetime) else c['time']
            metrics = metrics_map.get(ts, {})

            # Нормализуем время: если пришло как timestamp — конвертируем в datetime
            time_obj = c['time']
            if not isinstance(time_obj, datetime):
                time_obj = datetime.fromtimestamp(c['time'])

            bar = Bar(
                time=time_obj,
                open=float(c['open']),
                high=float(c['high']),
                low=float(c['low']),
                close=float(c['close']),
                volume=float(c.get('volume', 0)),
                metrics=metrics
            )
            bars.append(bar)

        return bars

    @staticmethod
    def fetch_and_join(db, ticker: str, timeframe: str, limit: int) -> List[Bar]:
        """
        Удобный метод: читает из БД и сразу склеивает.

        :param db: экземпляр DBManager
        :param ticker: тикер инструмента
        :param timeframe: таймфрейм
        :param limit: сколько баров запросить
        :return: List[Bar] в порядке ASC (старые → новые)
        """
        # 1. Получаем свечи (get_recent_candles возвращает DESC, разворачиваем)
        candles = db.get_recent_candles(ticker, timeframe, limit=limit)
        if not candles:
            return []
        candles_asc = list(reversed(candles))

        # 2. Получаем метрики (аналогично)
        metrics_raw = db.get_latest_metrics(ticker, timeframe, limit=limit)
        metrics_list = [
            {'time': m['time'], 'metrics': m.get('metrics', {})}
            for m in metrics_raw
        ]
        metrics_asc = list(reversed(metrics_list))

        # 3. Склеиваем
        return MetricsJoiner.join(candles_asc, metrics_asc)