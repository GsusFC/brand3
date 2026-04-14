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

CATEGORY_SUFFIXES = [
    "platform", "tool", "service", "solution", "app", "software",
    "infrastructure", "model", "models", "system", "systems",
    "engine", "engines", "lab", "labs", "layer", "protocol",
]

CATEGORY_STOPWORDS = {
    "that", "this", "with", "from", "your", "their", "about",
    "have", "been", "will", "more", "also", "can", "each",
    "making", "using", "used", "built", "designed", "made",
    "real", "world", "better", "next", "infinite", "predictions",
    "prediction", "teams", "company", "companies",
}


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

        category_signals = self._extract_category_signals(web)

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

        # Check if any of the brand's category concepts appear in Exa descriptions
        matches = 0
        matched_signals = []
        for signal in category_signals:
            key_words = self._signal_keywords(signal)
            if len(key_words) >= 2 and sum(1 for w in key_words if w in exa_text) >= 2:
                matches += 1
                matched_signals.append(signal)
            elif key_words and any(w in exa_text for w in key_words[:2]):
                matches += 1
                matched_signals.append(signal)

        ratio = matches / len(category_signals) if category_signals else 0
        score = 40 + (ratio * 60)  # 40-100 range

        return FeatureValue(
            "messaging_consistency",
            min(score, 100.0),
            raw_value=(
                f"categories: {category_signals[:3]}, "
                f"matched: {matched_signals[:3]}, "
                f"match_ratio: {ratio:.2f}"
            ),
            confidence=0.6,
            source="web_scrape+exa",
        )

    def _extract_category_signals(self, web: WebData) -> list[str]:
        signals = []

        hero_lines = []
        for line in web.markdown_content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("!["):
                continue
            if stripped.startswith("[") and "](" in stripped:
                continue
            if len(stripped) < 8:
                continue
            hero_lines.append(stripped.lower())
            if len(hero_lines) >= 12:
                break

        descriptive_lines = []
        for idx, line in enumerate(hero_lines):
            if idx == 0 and len(hero_lines) > 1:
                # Skip the headline when a descriptive subheadline exists below it.
                continue
            descriptive_lines.append(line)
        candidate_text = " ".join(descriptive_lines[:5])

        patterns = [
            rf'([a-z][\w-]*(?:\s+[a-z][\w-]*){{0,5}})\s+(?:{"|".join(CATEGORY_SUFFIXES)})\s+for\b',
            rf'(?:pre-trained|open-source|enterprise-grade|deterministic|frontier)?\s*([a-z][\w-]*(?:\s+[a-z][\w-]*){{0,5}})\s+(?:{"|".join(CATEGORY_SUFFIXES)})\b',
            r'([a-z][\w-]*(?:\s+[a-z][\w-]*){0,6})\s+for\s+[a-z][\w-]*(?:\s+[a-z][\w-]*){0,6}',
        ]
        for pattern in patterns:
            signals.extend(match.strip()[:60] for match in re.findall(pattern, candidate_text))

        for line in hero_lines:
            if any(suffix in line for suffix in CATEGORY_SUFFIXES):
                signals.append(line[:80])

        deduped = []
        seen = set()
        for signal in signals:
            normalized = " ".join(signal.split())
            normalized = re.sub(r"^[^a-z]+", "", normalized)
            if not normalized:
                continue
            keyword_tuple = tuple(self._signal_keywords(normalized))
            if normalized in seen or keyword_tuple in seen:
                continue
            if len(keyword_tuple) == 0:
                continue
            deduped.append(normalized)
            seen.add(normalized)
            seen.add(keyword_tuple)
        return deduped[:6]

    def _signal_keywords(self, signal: str) -> list[str]:
        words = re.findall(r"[a-z][a-z0-9-]+", signal.lower())
        keywords = []
        for word in words:
            if len(word) <= 3:
                continue
            if word in CATEGORY_STOPWORDS:
                continue
            keywords.append(word)
        return keywords[:4]

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
        brand_domain = ""
        if web.url:
            brand_domain = web.url.replace("https://", "").replace("http://", "").split("/")[0]

        # Check if web links to socials
        has_social_links = any(s in content for s in [
            "twitter.com", "x.com", "linkedin.com", "instagram.com",
            "facebook.com", "youtube.com", "tiktok.com",
        ])

        # Check if web has explicit contact info
        has_contact = any(s in content for s in [
            "contact", "email", "@", "phone", "address",
        ])

        # Early-stage startups often expose a form / waitlist / demo request instead of full social mesh.
        has_touchpoint = any(s in content for s in [
            "request demo", "book a demo", "get in touch", "talk to sales",
            "join waitlist", "waitlist", "apply", "your request has been received",
            "we will be in touch", "secure your place", "sign up", "sign in",
            "log in", "get started", "join the movement", "support the movement",
            "become a member", "create your petition", "create movement",
            "create petition", "support this cause",
        ])

        has_owned_surface = any(s in content for s in [
            "/docs", " docs", "/blog", " blog", "/about", " about",
            "/careers", " careers", "/privacy", "privacy policy", "terms",
            "/manifest", "manifest", "/search", "search?q=",
        ])

        # Check if social profiles mention the brand URL
        brand_url_mentioned = False
        if exa and exa.mentions:
            for r in exa.mentions:
                if brand_domain and brand_domain in (r.url or ""):
                    brand_url_mentioned = True
                    break

        score = 20.0 if web.title else 10.0
        if has_social_links:
            score += 25
        if has_contact:
            score += 20
        if has_touchpoint:
            score += 20
        if has_owned_surface:
            score += 10
        if brand_url_mentioned:
            score += 15

        return FeatureValue(
            "cross_channel_coherence",
            min(score, 100.0),
            raw_value=(
                f"social_links={has_social_links}, "
                f"contact={has_contact}, "
                f"touchpoint={has_touchpoint}, "
                f"owned_surface={has_owned_surface}, "
                f"brand_url_mentioned={brand_url_mentioned}"
            ),
            confidence=0.7,
            source="web_scrape+exa",
        )
