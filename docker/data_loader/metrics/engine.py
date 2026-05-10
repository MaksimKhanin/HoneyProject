# core/metrics/engine.py
"""
Движок для расчёта и сохранения метрик.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .registry import get_metric, list_metrics

logger = logging.getLogger(__name__)


class MetricsEngine:
    """
    Оркестратор расчёта метрик.

    Использование:
        engine = MetricsEngine(db)
        engine.calculate_for_candles(ticker, timeframe, candles)
    """

    # 🔥 Класс-переменная для ограничения памяти (настраивается глобально)
    MAX_CANDLES_CACHE: int = 2000

    def __init__(self, db, metric_names: Optional[List[str]] = None):
        """
        :param db: экземпляр DBManager
        :param metric_names: список имён метрик для расчёта (None = все)
        """
        self.db = db
        self.metric_names = metric_names or list_metrics()
        self.metrics = [get_metric(name) for name in self.metric_names]

        # 🔥 ВЫЧИСЛЯЕМ, сколько свечей нужно минимум
        # Это ключевая строка — без неё recommended_fetch_limit упадёт!
        self.min_candles_required = max(
            (m.min_candles for m in self.metrics),
            default=10  # fallback, если метрик нет
        )

        logger.info(
            f"✅ MetricsEngine инициализирован: {len(self.metrics)} метрик, "
            f"мин. свечей: {self.min_candles_required}"
        )

    @property
    def recommended_fetch_limit(self) -> int:
        """
        Рекомендуемое количество свечей для запроса из БД.
        Берём минимум + буфер 20% на случай пропуска данных.
        """
        return int(self.min_candles_required * 1.2) + 10

    def calculate_for_candles(
            self,
            ticker: str,
            timeframe: str,
            candles: List[Dict[str, Any]],
            candle_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Рассчитывает все зарегистрированные метрики для набора свечей.

        :return: объединённый dict всех метрик {"rsi_14": ..., "volatility_20": ..., ...}
        """
        if not candles:
            logger.warning(f"⚠️ Нет свечей для расчёта метрик: {ticker}/{timeframe}")
            return {}

        # Сортируем свечи по времени (от старых к новым)
        candles_sorted = sorted(candles, key=lambda c: c['time'])
        candle_time = candle_time or candles_sorted[-1]['time']

        results = {}

        for metric in self.metrics:
            try:
                metric_result = metric.calculate(
                    ticker=ticker,
                    timeframe=timeframe,
                    candles=candles_sorted,
                    db=self.db
                )
                results.update(metric_result)
            except Exception as e:
                logger.error(f"❌ Ошибка в метрике {metric.name}: {e}", exc_info=True)
                continue

        if results:
            # Сохраняем в БД
            self._save_metrics(ticker, timeframe, candle_time, results)
            logger.debug(f"✅ Сохранено {len(results)} метрик для {ticker}/{timeframe}@{candle_time}")

        return results

    def _save_metrics(
            self,
            ticker: str,
            timeframe: str,
            candle_time: datetime,
            metrics: Dict[str, Any]
    ):
        """Сохраняет метрики в таблицу metrics через DBManager."""
        try:
            self.db.save_metrics(
                ticker=ticker,
                timeframe=timeframe,
                candle_time=candle_time,
                metrics=metrics
            )
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения метрик в БД: {e}", exc_info=True)

    def calculate_batch(
            self,
            data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Массовый расчёт метрик для нескольких (ticker, timeframe, candles).

        :param data: список dict с ключами ['ticker', 'timeframe', 'candles']
        :return: статистика выполнения
        """
        stats = {"total": len(data), "success": 0, "failed": 0, "errors": []}

        for item in data:
            try:
                self.calculate_for_candles(
                    ticker=item['ticker'],
                    timeframe=item['timeframe'],
                    candles=item['candles']
                )
                stats["success"] += 1
            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append(f"{item.get('ticker')}/{item.get('timeframe')}: {e}")
                logger.error(f"❌ Ошибка в батче: {e}", exc_info=True)

        logger.info(f"📊 MetricsEngine batch: {stats['success']}/{stats['total']} успешно")
        return stats

    def get_requirements_report(self) -> Dict[str, Any]:
        """Возвращает отчёт о требованиях метрик (для дебага)."""
        return {
            "metrics": [
                {"name": m.name, "min_candles": m.min_candles, "desc": m.description}
                for m in self.metrics
            ],
            "min_candles_required": self.min_candles_required,
            "recommended_fetch_limit": self.recommended_fetch_limit,
        }