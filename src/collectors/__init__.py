"""Collectors package for Brand3 Scoring."""

from .web_collector import WebCollector, WebData
from .context_collector import ContextCollector, ContextData
from .exa_collector import ExaCollector, ExaData
from .competitor_collector import CompetitorCollector, CompetitorData, ComparisonResult

try:
    from .social_collector import SocialCollector, SocialData, PlatformMetrics
except ImportError:
    pass

__all__ = [
    "WebCollector", "WebData",
    "ContextCollector", "ContextData",
    "ExaCollector", "ExaData",
    "CompetitorCollector", "CompetitorData", "ComparisonResult",
]
