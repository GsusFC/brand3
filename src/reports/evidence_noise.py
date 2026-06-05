"""Shared deterministic filters for public evidence noise."""

from __future__ import annotations

import re


def looks_like_article_or_product_card_feed(text: str) -> bool:
    """Detect concatenated editorial/product-card feeds masquerading as evidence."""
    low = str(text or "").strip().lower()
    if len(low) < 120:
        return False
    date_hits = len(
        re.findall(
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},\s+20\d{2}\b",
            low,
        )
    )
    if date_hits >= 2:
        return True
    if "the only subscription you need" in low and "newsletter" in low and "podcast" in low:
        return True
    if "how we run a" in low and "dispatches from" in low:
        return True
    if "how we run a" in low and "what i learned" in low:
        return True
    if "how we run a" in low and "build your own financial analyst" in low:
        return True
    if "when your vibe coded app" in low and "the new rules of writing" in low:
        return True
    if "open with plus one" in low and ("link copied" in low or "share source code" in low):
        return True
    if "custom agents camp" in low and ("subscribers" in low or "partnership with" in low):
        return True
    if "paid subscribers" in low and ("product managers" in low or "ai agents" in low):
        return True
    marker_hits = sum(
        1
        for marker in (
            "read the report",
            "get in your inbox",
            "newsletter",
            "podcast",
            "dispatches from",
            "notes from",
            "playtesting notes",
            "after automation",
            "how we run a",
            "what i learned",
            "paid subscribers",
            "the folder is the agent",
            "product managers",
            "plus:",
        )
        if marker in low
    )
    return marker_hits >= 3
