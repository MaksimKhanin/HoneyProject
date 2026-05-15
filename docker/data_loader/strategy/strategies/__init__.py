# strategies/__init__.py
from .trailing_trend import TrailingTrendStrategy
from .trend_hunter import TrendHunterStrategy

__all__ = ["TrailingTrendStrategy", "TrendHunterStrategy"]