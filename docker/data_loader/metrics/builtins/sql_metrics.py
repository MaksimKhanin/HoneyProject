# core/metrics/builtins/sql_metrics.py
"""
Встроенные метрики, рассчитываемые через SQL.
Используем подзапросы для ORDER BY + LIMIT перед агрегацией (требование PostgreSQL).
"""

from typing import Dict, Any
from metrics.base import  SQLMetric
from metrics.registry import register_metric

@register_metric
class VolumeAvgMetric(SQLMetric):
    """Средний объём за последние 20 свечей."""
    name = "volume_avg_20"
    description = "Средний объём за 20 свечей"
    sql_query = """
        SELECT AVG(vol) FROM (
            SELECT volume as vol 
            FROM candles 
            WHERE ticker = %s AND timeframe = %s 
            ORDER BY time DESC LIMIT 20
        ) sub
    """

    def post_process(self, row: tuple) -> Dict[str, Any]:
        return {"volume_avg_20": float(row[0]) if row[0] else None}


@register_metric
class PriceRangeMetric(SQLMetric):
    """Средний диапазон цены (high - low) за 10 свечей."""
    name = "price_range_10"
    description = "Средний диапазон (high-low) за 10 свечей"
    sql_query = """
        SELECT AVG(rng) FROM (
            SELECT (high - low) as rng 
            FROM candles 
            WHERE ticker = %s AND timeframe = %s 
            ORDER BY time DESC LIMIT 10
        ) sub
    """

    def post_process(self, row: tuple) -> Dict[str, Any]:
        return {"price_range_10": float(row[0]) if row[0] else None}


@register_metric
class CandleCountMetric(SQLMetric):
    """Количество свечей за последние 24 часа."""
    name = "candle_count_24h"
    description = "Количество свечей за последние 24 часа"
    sql_query = """
        SELECT COUNT(*)
        FROM candles
        WHERE ticker = %s AND timeframe = %s
        AND time >= NOW() - INTERVAL '24 hours'
    """

    def post_process(self, row: tuple) -> Dict[str, Any]:
        return {"candle_count_24h": int(row[0]) if row[0] else 0}