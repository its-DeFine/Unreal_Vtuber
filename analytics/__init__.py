"""Analytics module providing a minimal abstract interface."""

from .base import AnalyticsBase
from .in_memory import InMemoryAnalytics
from .metabase import MetabaseAnalytics

__all__ = ["AnalyticsBase", "InMemoryAnalytics", "MetabaseAnalytics"]
