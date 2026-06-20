"""Brand3 market classification primitives.

This package is deliberately separate from scoring. Classifications provide
context for search, filtering, benchmarking, and company profiles; they do not
change SV9 or legacy scores.
"""

from src.classification.schemas import ClassificationTag, MarketClassification

__all__ = ["ClassificationTag", "MarketClassification"]
