"""
Coherencia feature extractor.

Measures if messaging, visual identity, and tone are CONSISTENT
across all touchpoints.

Data sources: web scrape, social profiles (TODO), Exa
"""

import re
from collections import Counter
from ..models.brand import FeatureValue
from ..collectors.web_collector import WebData
from ..collectors.exa_collector import ExaData
from .visual_analyzer import VisualAnalyzer


# Common generic marketing phrases (red flag for brand consistency)
GENERIC_PHRASES = [
    "best in class", "cutting edge", "world class", "state of the art",
    "innovative solutions", "leading provider", "industry leading",
    "next level", "game changer", "disrupting", "revolutionary",
    "seamless", "end to end", "one stop shop", "turnkey",
    "synergy", "empower", "leverage", "holistic approach",
    "customer centric", "data driven", "scalable solutions",
    "we are passionate", "our mission is", "we believe in",
    "driving results", "unlocking potential", "transforming",
    "award winning", "trusted by", "global leader",
]


class CoherenciaExtractor:
    """Extract coherencia features."""

    def __init__(self, visual_analyzer: VisualAnalyzer = None, skip_visual_analysis: bool = False):
        self.visual_analyzer = visual_analyzer or VisualAnalyzer()
        self.skip_visual_analysis = skip_visual_analysis

    def extract(self, web: WebData = None, exa: ExaData = None) -> dict[str, FeatureValue]:
        features = {}
        features["visual_consistency"] = self._visual_consistency(web)
        features["messaging_consistency"] = self._messaging_consistency(web, exa)
        features["tone_consistency"] = self._tone_consistency(web, exa)
        features["cross_channel_coherence"] = self._cross_channel_coherence(web, exa)
        return features

    def _visual_consistency(self, web: WebData = None) -> FeatureValue:
        """
        Are colors, typography, and imagery consistent?
        Uses VisualAnalyzer to take a screenshot and analyze it with AI vision.
        Falls back to heuristic scoring if screenshot or vision fails.
        """
        if not web or web.error:
            return FeatureValue("visual_consistency", 0.0, confidence=0.3, source="none")

        brand_name = web.title or ""

        if self.skip_visual_analysis:
            content = web.markdown_content.lower()
            brand_in_header = web.title and len(web.title) > 0
            has_style = any(s in content for s in ["style guide", "brand guidelines", "logo"])

            score = 40.0
            if brand_in_header:
                score += 20
            if has_style:
                score += 10

            return FeatureValue(
                "visual_consistency",
                min(score, 100.0),
                raw_value="benchmark heuristic fallback (visual analysis skipped)",
                confidence=0.25,
                source="web_scrape_heuristic",
            )

        # If we already have a screenshot from the web scrape, use it
        if web.screenshot_path and web.screenshot_path.startswith("http"):
            result = self.visual_analyzer.analyze_screenshot(
                web.screenshot_path, brand_name
            )
        else:
            # Take a new screenshot and analyze
            result = self.visual_analyzer.analyze_url(web.url, brand_name)

        if result.error:
            # Screenshot/vision failed — fall back to content heuristics
            content = web.markdown_content.lower()
            brand_in_header = web.title and len(web.title) > 0
            has_style = any(s in content for s in ["style guide", "brand guidelines", "logo"])

            score = 40.0
            if brand_in_header:
                score += 20
            if has_style:
                score += 10

            return FeatureValue(
                "visual_consistency",
                min(score, 100.0),
                raw_value=f"heuristic fallback (screenshot error: {result.error[:80]})",
                confidence=0.3,
                source="web_scrape_heuristic",
            )

        # Build raw_value summary from analysis details
        details = result.details or {}
        dominant_colors = details.get("dominant_colors", [])
        style = details.get("style", "unknown")
        method = details.get("method", "unknown")

        raw_summary = (
            f"score={result.overall_score:.0f}, "
            f"logo={'detected' if result.logo_detected else 'not found'}, "
            f"colors={dominant_colors[:3]}, "
            f"style={style}, "
            f"method={method}"
        )

        return FeatureValue(
            "visual_consistency",
            result.overall_score,
            raw_value=raw_summary,
            confidence=result.confidence,
            source="visual_analysis",
        )

    def _messaging_consistency(self, web: WebData = None, exa: ExaData = None) -> FeatureValue:
        """
        Do all channels describe the brand with the same CORE CONCEPTS?
        
        NOT keyword overlap (web copy ≠ press coverage).
        Instead: does the brand's CATEGORY + VALUE PROP appear consistently?
        
        Example: Stripe says "financial infrastructure" on their site.
        If Exa results also call them "payments" or "financial infrastructure" = consistent.
        If Exa calls them "SaaS startup" while they say "infrastructure" = mismatch.
        """
        if not web:
            return FeatureValue("messaging_consistency", 0.0, confidence=0.3, source="none")

        content = web.markdown_content.lower()

        # ── Extract brand CATEGORY from web (what do they say they are?) ──
        # Look for "X for Y", "the Y platform", "Y tool/service/solution"
        category_signals = []
        category_patterns = [
            r'(?:the\s+)?(\w[\w\s]{3,30})\s+(?:platform|tool|service|solution|app|software)',
            r'(?:built|designed|made)\s+(?:for|to)\s+(\w[\w\s]{3,30})',
            r'(?:a|the)\s+(\w[\w\s]{3,30})\s+(?:for|that|which)',
        ]
        for pattern in category_patterns:
            matches = re.findall(pattern, content[:2000])
            category_signals.extend(m.strip()[:40] for m in matches)

        if not category_signals:
            # No clear category positioning — that's a problem
            return FeatureValue(
                "messaging_consistency",
                35.0,
                raw_value="no clear category positioning found",
                confidence=0.5,
                source="web_scrape",
            )

        # ── Check if Exa mentions use similar categories ──
        if not exa or not exa.mentions:
            return FeatureValue(
                "messaging_consistency",
                55.0,
                raw_value=f"categories: {category_signals[:3]}, no Exa data",
                confidence=0.4,
                source="web_scrape",
            )

        exa_text = " ".join(
            ((r.text or "") + " " + (r.title or "")).lower()[:500]
            for r in exa.mentions[:8]
        )

        # Check if any of the brand's category words appear in Exa descriptions
        matches = 0
        for signal in category_signals:
            # Extract 2-3 key words from each category signal
            key_words = [w for w in signal.split() if len(w) > 3 and w not in {
                "that", "this", "with", "from", "your", "their", "about",
                "have", "been", "will", "more", "also", "can", "each"
            }]
            if any(w in exa_text for w in key_words[:3]):
                matches += 1

        ratio = matches / len(category_signals) if category_signals else 0
        score = 40 + (ratio * 60)  # 40-100 range

        return FeatureValue(
            "messaging_consistency",
            min(score, 100.0),
            raw_value=f"categories: {category_signals[:3]}, match_ratio: {ratio:.2f}",
            confidence=0.6,
            source="web_scrape+exa",
        )

    def _tone_consistency(self, web: WebData = None, exa: ExaData = None) -> FeatureValue:
        """
        Is the tone of communication consistent across channels?
        Heuristic: check formality level, use of jargon, sentence structure.
        """
        if not web:
            return FeatureValue("tone_consistency", 0.0, confidence=0.3, source="none")

        content = web.markdown_content

        # Formality indicators
        formal_signals = ["furthermore", "therefore", "consequently", "regarding",
                          "herein", "aforementioned", "pursuant"]
        informal_signals = ["hey", "awesome", "cool", "gonna", "wanna",
                            "let's go", "!", "🔥", "💪"]

        formal_count = sum(1 for s in formal_signals if s in content.lower())
        informal_count = sum(1 for s in informal_signals if s in content.lower())

        # If mixed formal and informal heavily, it's inconsistent
        if formal_count > 3 and informal_count > 3:
            score = 35.0  # Mixed tone = inconsistent
        elif formal_count > 0 or informal_count > 0:
            score = 70.0  # Has a clear tone
        else:
            score = 55.0  # Neutral / hard to tell

        # TODO: Compare with social media tone when available

        return FeatureValue(
            "tone_consistency",
            score,
            raw_value=f"formal={formal_count}, informal={informal_count}",
            confidence=0.5,
            source="web_scrape",
        )

    def _cross_channel_coherence(self, web: WebData = None, exa: ExaData = None) -> FeatureValue:
        """
        Do the channels link to each other and reference each other correctly?
        """
        if not web:
            return FeatureValue("cross_channel_coherence", 0.0, confidence=0.3, source="none")

        content = web.markdown_content.lower()

        # Check if web links to socials
        has_social_links = any(s in content for s in [
            "twitter.com", "x.com", "linkedin.com", "instagram.com",
            "facebook.com", "youtube.com", "tiktok.com",
        ])

        # Check if web has contact info
        has_contact = any(s in content for s in [
            "contact", "email", "@", "phone", "address",
        ])

        # Check if social profiles mention the brand URL
        brand_url_mentioned = False
        if exa and exa.mentions:
            for r in exa.mentions:
                if web.url and web.url.replace("https://", "").replace("http://", "").split("/")[0] in r.url:
                    brand_url_mentioned = True
                    break

        score = 0.0
        if has_social_links:
            score += 40
        if has_contact:
            score += 30
        if brand_url_mentioned:
            score += 30

        return FeatureValue(
            "cross_channel_coherence",
            min(score, 100.0),
            raw_value=f"social_links={has_social_links}, contact={has_contact}",
            confidence=0.7,
            source="web_scrape+exa",
        )
