"""
Presencia feature extractor.

Measures where the brand can actually be found: owned web, socials, search
discoverability, and directory presence.

All features return structured `raw_value` payloads so downstream consumers can
surface evidence instead of opaque numbers.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from urllib.parse import urlparse

from ..collectors.context_collector import ContextData
from ..collectors.exa_collector import ExaData
from ..collectors.social_collector import SocialData
from ..collectors.web_collector import WebData
from ..models.brand import FeatureValue


class PresenciaExtractor:
    """Extract presencia features from collected web, Exa, and social data."""

    PLATFORM_WEIGHTS = {
        "linkedin": 1.0,
        "github": 1.0,
        "twitter": 0.9,
        "youtube": 0.8,
        "instagram": 0.8,
        "tiktok": 0.7,
        "facebook": 0.6,
    }

    TIER1_DIRECTORIES = (
        "crunchbase.com",
        "linkedin.com/company",
        "g2.com",
        "capterra.com",
    )
    TIER2_DIRECTORIES = (
        "yelp.com",
        "glassdoor.com",
        "trustpilot.com",
        "angel.co",
        "angellist.com",
        "producthunt.com",
    )

    @staticmethod
    def _subject_relevance(result, brand_name: str) -> float:
        """Estimate whether the brand is central in the result, not just mentioned in passing."""
        brand_lower = (brand_name or "").strip().lower()
        if not brand_lower:
            return 0.5

        title = (getattr(result, "title", "") or "").lower()
        url = (getattr(result, "url", "") or "").lower()
        text = (
            (getattr(result, "text", "") or "")
            + " "
            + (getattr(result, "summary", "") or "")
        ).lower()

        if brand_lower in title or brand_lower in url:
            return 1.0
        if brand_lower in text:
            return 0.7
        return 0.35

    @staticmethod
    def _normalize_relevance(score: float) -> float:
        """Normalize Exa score to a useful 0-1 range."""
        if score is None:
            return 0.4
        try:
            numeric = float(score)
        except (TypeError, ValueError):
            return 0.4
        if numeric <= 0:
            return 0.2
        if numeric >= 1:
            return 1.0
        return numeric

    @staticmethod
    def _meaningful_content(content: str | None) -> str:
        if not content:
            return ""
        lines = []
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("!["):
                continue
            if line.startswith("[") and "](" in line:
                continue
            lines.append(line)
            if len(" ".join(lines)) >= 180:
                break
        return " ".join(lines).strip()

    @staticmethod
    def _snippet(text: str, limit: int = 150) -> str | None:
        if not text:
            return None
        text = " ".join(text.split())
        return text[:limit]

    @staticmethod
    def _extract_domain(url: str | None) -> str | None:
        if not url:
            return None
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = (parsed.netloc or parsed.path or "").strip().lower()
        if host.startswith("www."):
            host = host[4:]
        return host or None

    @staticmethod
    def _parse_last_post_days_ago(last_post_date: str | None) -> int | None:
        if not last_post_date:
            return None
        value = last_post_date.strip()
        lowered = value.lower()
        if "ago" in lowered:
            parts = lowered.split()
            try:
                amount = int(parts[0])
            except (IndexError, ValueError):
                return None
            if "hour" in lowered:
                return 0
            if "day" in lowered:
                return amount
            if "week" in lowered:
                return amount * 7
            if "month" in lowered:
                return amount * 30
            return None
        for fmt in ("%Y-%m-%d", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"):
            try:
                parsed = datetime.strptime(value, fmt)
                return max((datetime.now() - parsed).days, 0)
            except ValueError:
                continue
        return None

    def extract(
        self,
        web: WebData = None,
        exa: ExaData = None,
        social: SocialData = None,
        context: ContextData = None,
    ) -> dict[str, FeatureValue]:
        return {
            "web_presence": self._web_presence(web, context=context),
            "social_footprint": self._social_footprint(social),
            "search_visibility": self._search_visibility(exa),
            "directory_presence": self._directory_presence(exa),
            "context_readiness": self._context_readiness(context),
        }

    def _web_presence(self, web: WebData = None, context: ContextData = None) -> FeatureValue:
        """Does the brand have a real owned web presence with basic structure?"""
        if not web or web.error:
            return FeatureValue(
                "web_presence",
                15.0,
                raw_value={
                    "has_https": False,
                    "page_status": "missing",
                    "title": getattr(web, "title", "") or "",
                    "evidence_snippet": None,
                    "signals_detected": ["no_web_data"],
                },
                confidence=0.4,
                source="web_scrape",
            )

        content = (web.markdown_content or "").lower()
        meaningful = self._meaningful_content(web.markdown_content)
        signals_detected: list[str] = []
        placeholder_signals = [
            "this domain is for use in",
            "domain is parked",
            "coming soon",
            "under construction",
            "this page is not available",
            "buy this domain",
            "domain for sale",
            "default web server page",
            "welcome to nginx",
            "apache2 ubuntu default page",
            "this site can't be reached",
            "it works!",
        ]
        title_lower = (web.title or "").lower()
        is_placeholder = any(signal in content for signal in placeholder_signals)
        has_real_title = bool(web.title and not any(s in title_lower for s in ["default", "welcome", "coming soon"]))
        if is_placeholder and not has_real_title:
            return FeatureValue(
                "web_presence",
                5.0,
                raw_value={
                    "has_https": web.url.startswith("https://"),
                    "page_status": "placeholder",
                    "title": web.title or "",
                    "evidence_snippet": self._snippet(meaningful or web.markdown_content or ""),
                    "signals_detected": ["placeholder_detected"],
                },
                confidence=0.95,
                source="web_scrape",
            )

        score = 0.0
        page_status = "live"
        if len(meaningful) >= 100:
            score += 40.0
            signals_detected.append("meaningful_content")
        elif len(meaningful) >= 24:
            page_status = "thin"
            signals_detected.append("thin_content")
        else:
            page_status = "minimal"
            signals_detected.append("no_meaningful_content")

        if web.url.startswith("https://"):
            score += 10.0
            signals_detected.append("https")

        if web.title:
            score += 10.0
            signals_detected.append("clear_title")

        structure_score = 0.0
        if any(token in content for token in ["pricing", "about", "contact", "docs", "features", "solutions", "login", "get started"]):
            structure_score += 5.0
            signals_detected.append("nav_structure")
        if any(token in content for token in ["privacy", "terms", "copyright", "all rights reserved", "©"]):
            structure_score += 5.0
            signals_detected.append("footer_structure")
        if web.meta_description:
            structure_score += 5.0
            signals_detected.append("meta_description")
        if context:
            if context.sitemap_found:
                structure_score += 3.0
                signals_detected.append("sitemap")
            if context.robots_found:
                structure_score += 2.0
                signals_detected.append("robots")
            if context.schema_types:
                structure_score += 3.0
                signals_detected.append("schema")
            if context.key_pages.get("about"):
                structure_score += 2.0
                signals_detected.append("about_page")
        score += structure_score

        identity_bonus = 0.0
        title_words = {word for word in (web.title or "").lower().split() if len(word) > 2}
        meta_lower = (web.meta_description or "").lower()
        if title_words and any(word in meta_lower for word in title_words):
            identity_bonus += 10.0
            signals_detected.append("consistent_identity")
        elif web.title:
            identity_bonus += 5.0
            signals_detected.append("brand_title_present")
        score += identity_bonus

        return FeatureValue(
            "web_presence",
            min(score, 100.0),
            raw_value={
                "has_https": web.url.startswith("https://"),
                "page_status": page_status,
                "title": web.title or "",
                "evidence_snippet": self._snippet(meaningful),
                "signals_detected": signals_detected,
                "context_readiness": {
                    "context_score": context.context_score,
                    "coverage": context.coverage,
                    "confidence": context.confidence,
                    "schema_types": context.schema_types,
                    "key_pages": context.key_pages,
                } if context else None,
            },
            confidence=0.9 if len(meaningful) >= 100 else 0.6,
            source="web_scrape",
        )

    def _context_readiness(self, context: ContextData = None) -> FeatureValue:
        if not context:
            return FeatureValue(
                "context_readiness",
                0.0,
                raw_value={"reason": "no_context_scan"},
                confidence=0.0,
                source="context",
            )
        return FeatureValue(
            "context_readiness",
            float(context.context_score),
            raw_value={
                "robots_found": context.robots_found,
                "sitemap_found": context.sitemap_found,
                "sitemap_url_count": context.sitemap_url_count,
                "llms_txt_found": context.llms_txt_found,
                "schema_types": context.schema_types,
                "key_pages": context.key_pages,
                "avg_words": context.avg_words,
                "avg_internal_links": context.avg_internal_links,
                "opportunities": context.opportunities,
                "confidence_reason": context.confidence_reason,
            },
            confidence=float(context.confidence),
            source="context",
        )

    def _social_footprint(self, social: SocialData = None) -> FeatureValue:
        """Score platform mix, scale, and activity using scraped social profiles."""
        if not social or not social.platforms:
            return FeatureValue(
                "social_footprint",
                15.0,
                raw_value={
                    "reason": "no_social_data",
                    "platforms": [],
                    "total_followers": 0,
                    "active_platforms_count": 0,
                    "professional_presence": False,
                    "consumer_presence": False,
                },
                confidence=0.3,
                source="social_scrape",
            )

        score = 0.0
        num_platforms = len(social.platforms)
        if num_platforms == 1:
            score = 25.0
        elif num_platforms == 2:
            score = 40.0
        elif num_platforms <= 4:
            score = 55.0 + (num_platforms - 2) * 10
        else:
            score = 75.0 + min(num_platforms - 4, 3) * 8

        if social.total_followers >= 1_000_000:
            score += 20.0
        elif social.total_followers >= 100_000:
            score += 15.0
        elif social.total_followers >= 10_000:
            score += 10.0
        elif social.total_followers >= 1_000:
            score += 5.0

        if social.avg_post_frequency >= 7:
            score += 5.0
        elif social.avg_post_frequency >= 1:
            score += 3.0

        verified_count = sum(1 for metrics in social.platforms.values() if metrics.verified)
        if verified_count > 0:
            score += min(verified_count * 3.0, 10.0)

        platform_payload = []
        active_platforms_count = 0
        professional_presence = False
        consumer_presence = False
        for name, metrics in sorted(social.platforms.items()):
            days_ago = self._parse_last_post_days_ago(metrics.last_post_date)
            if metrics.posts_last_30_days > 0 or days_ago is not None:
                active_platforms_count += 1
            if name in {"linkedin", "github"}:
                professional_presence = True
            if name in {"instagram", "tiktok"}:
                consumer_presence = True
            platform_payload.append(
                {
                    "name": name,
                    "url": metrics.profile_url,
                    "followers": metrics.followers_count,
                    "verified": metrics.verified,
                    "last_post_days_ago": days_ago,
                }
            )

        return FeatureValue(
            "social_footprint",
            min(score, 100.0),
            raw_value={
                "platforms": platform_payload,
                "total_followers": social.total_followers,
                "active_platforms_count": active_platforms_count,
                "professional_presence": professional_presence,
                "consumer_presence": consumer_presence,
            },
            confidence=0.85,
            source="social_scrape",
        )

    def _search_visibility(self, exa: ExaData = None) -> FeatureValue:
        """Combine search mentions and AI visibility into a single discoverability score."""
        if not exa:
            return FeatureValue(
                "search_visibility",
                15.0,
                raw_value={
                    "search_results_count": 0,
                    "relevant_results_count": 0,
                    "own_url_in_top3": False,
                    "ai_visibility_signals": 0,
                    "top_domains": [],
                    "evidence": [],
                },
                confidence=0.4,
                source="exa",
            )

        relevant_mentions = [
            result
            for result in exa.mentions
            if self._subject_relevance(result, exa.brand_name) > 0.35
        ]
        relevant_count = len(relevant_mentions)
        if relevant_count >= 12:
            score = 70.0
        elif relevant_count >= 8:
            score = 58.0
        elif relevant_count >= 5:
            score = 45.0
        elif relevant_count >= 3:
            score = 32.0
        elif relevant_count >= 1:
            score = 20.0
        else:
            score = 10.0

        brand_lower = (exa.brand_name or "").lower()
        own_url_in_top3 = any(brand_lower in (result.url or "").lower() for result in exa.mentions[:3])
        if own_url_in_top3:
            score += 10.0

        ai_visibility_signals = 0
        ai_weighted_sum = 0.0
        for result in exa.ai_visibility_results[:5]:
            relevance = self._normalize_relevance(getattr(result, "score", 0.0))
            subject_relevance = self._subject_relevance(result, exa.brand_name)
            contribution = 30.0 * relevance * subject_relevance
            ai_weighted_sum += contribution
            if contribution >= 12.0:
                ai_visibility_signals += 1
        if ai_weighted_sum >= 55.0:
            score += 20.0
        elif ai_weighted_sum >= 35.0:
            score += 14.0
        elif ai_weighted_sum >= 18.0:
            score += 8.0
        elif ai_visibility_signals >= 1:
            score += 4.0

        domain_counter = Counter()
        for result in relevant_mentions:
            domain = self._extract_domain(result.url)
            if domain:
                domain_counter[domain] += 1

        evidence = []
        for result in relevant_mentions[:3]:
            evidence.append(
                {
                    "url": result.url,
                    "title": result.title,
                    "snippet": self._snippet((result.summary or result.text or "").strip()),
                }
            )

        return FeatureValue(
            "search_visibility",
            min(score, 100.0),
            raw_value={
                "search_results_count": len(exa.mentions),
                "relevant_results_count": relevant_count,
                "own_url_in_top3": own_url_in_top3,
                "ai_visibility_signals": ai_visibility_signals,
                "top_domains": [domain for domain, _ in domain_counter.most_common(3)],
                "evidence": evidence,
            },
            confidence=0.75 if relevant_count > 0 else 0.5,
            source="exa",
        )

    def _directory_presence(self, exa: ExaData = None) -> FeatureValue:
        """Presence in tiered structured directories and review platforms."""
        if not exa or not exa.mentions:
            return FeatureValue(
                "directory_presence",
                0.0,
                raw_value={"tier1_found": [], "tier2_found": [], "total_points": 0},
                confidence=0.4,
                source="exa",
            )

        tier1_found = []
        tier2_found = []
        seen_tier1 = set()
        seen_tier2 = set()
        for result in exa.mentions:
            url = (result.url or "").lower()
            for domain in self.TIER1_DIRECTORIES:
                if domain in url and domain not in seen_tier1:
                    seen_tier1.add(domain)
                    tier1_found.append(domain)
            for domain in self.TIER2_DIRECTORIES:
                if domain in url and domain not in seen_tier2:
                    seen_tier2.add(domain)
                    tier2_found.append(domain)

        total_points = (len(tier1_found) * 20) + (len(tier2_found) * 8)
        return FeatureValue(
            "directory_presence",
            min(float(total_points), 100.0),
            raw_value={
                "tier1_found": tier1_found,
                "tier2_found": tier2_found,
                "total_points": total_points,
            },
            confidence=0.7,
            source="exa",
        )
