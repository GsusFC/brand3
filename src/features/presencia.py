"""
Presencia feature extractor.

Measures WHERE the brand appears and with WHAT VOLUME.
Data sources: web scrape, Exa search, social media profiles

KEY INSIGHT: Strong brands (Apple) have MINIMAL websites.
Don't penalize minimalism — measure brand reach instead.
"""

from ..models.brand import FeatureValue
from ..collectors.web_collector import WebData
from ..collectors.exa_collector import ExaData
from ..collectors.social_collector import SocialData


class PresenciaExtractor:
    """Extract presencia features from raw collected data."""

    PLATFORM_WEIGHTS = {
        "linkedin": 1.0,
        "github": 1.0,
        "twitter": 0.9,
        "youtube": 0.8,
        "instagram": 0.8,
        "tiktok": 0.7,
        "facebook": 0.6,
    }

    PLATFORM_GROUPS = {
        "linkedin": "professional",
        "github": "builder",
        "twitter": "social",
        "youtube": "social",
        "instagram": "social",
        "tiktok": "social",
        "facebook": "social",
    }

    @staticmethod
    def _subject_relevance(result, brand_name: str) -> float:
        """Estimate whether the brand is central in the result, not just mentioned in passing."""
        brand_lower = (brand_name or "").strip().lower()
        if not brand_lower:
            return 0.5

        title = (result.title or "").lower()
        url = (result.url or "").lower()
        text = ((result.text or "") + " " + (result.summary or "")).lower()

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

    def extract(
        self,
        web: WebData = None,
        exa: ExaData = None,
        social: SocialData = None
    ) -> dict[str, FeatureValue]:
        features = {}
        features["web_presence"] = self._web_presence(web, exa)
        features["social_footprint"] = self._social_footprint(web, exa, social)
        features["search_visibility"] = self._search_visibility(exa)
        features["ai_visibility"] = self._ai_visibility(exa)
        features["directory_listings"] = self._directory_listings(exa)
        return features

    def _web_presence(self, web: WebData = None, exa: ExaData = None) -> FeatureValue:
        """
        Does the brand have a real website?
        
        NOT measured by content volume (Apple proves that wrong).
        Measured by: professional domain, HTTPS, clear identity, structure.
        """
        if not web or web.error:
            return FeatureValue("web_presence", 0.0, confidence=0.8, source="web_scrape")

        score = 0.0
        content = web.markdown_content.lower()

        # ── Base: has a real website at all ──
        # Having any meaningful page is already 40 points
        if len(web.markdown_content) > 100:
            score += 40

        # ── Placeholder/parked page detection ──
        placeholder_signals = [
            "this domain is for use in", "domain is parked", "coming soon",
            "under construction", "this page is not available",
            "buy this domain", "domain for sale", "default web server page",
            "welcome to nginx", "apache2 ubuntu default page",
            "this site can't be reached", "it works!",
        ]
        if any(s in content for s in placeholder_signals):
            # But don't flag if the page has a real brand title
            # (SPAs like Linear return minimal content but have real titles)
            if web.title and len(web.title) > 10 and not any(s in web.title.lower() for s in ["default", "welcome", "coming soon"]):
                pass  # Has a real title — probably a SPA, not a placeholder
            else:
                return FeatureValue(
                    "web_presence", 5.0,
                    raw_value="placeholder/parked page detected",
                    confidence=0.95, source="web_scrape",
                )

        # ── Professional signals (not content volume) ──
        
        # Has a clear title / brand identity
        if web.title and len(web.title) > 0:
            score += 15

        # HTTPS (basic professionalism)
        if web.url.startswith("https://"):
            score += 10

        # Has SOME navigation (even Apple has Store, Mac, iPad, etc.)
        nav_signals = ["products", "about", "contact", "pricing", "services",
                       "blog", "docs", "features", "solutions", "store",
                       "mac", "iphone", "ipad", "watch", "developers",
                       "enterprise", "resources", "support", "help",
                       "login", "sign in", "get started", "download"]
        nav_count = sum(1 for s in nav_signals if s in content)
        score += min(nav_count * 3, 20)

        # Has CTA / conversion elements (the site wants you to DO something)
        cta_signals = ["sign up", "get started", "try", "buy", "contact us",
                       "request demo", "free trial", "subscribe", "order",
                       "shop", "purchase", "register", "create account"]
        cta_count = sum(1 for s in cta_signals if s in content)
        score += min(cta_count * 4, 15)

        return FeatureValue(
            "web_presence",
            min(score, 100.0),
            raw_value=f"{len(web.markdown_content)} chars, {nav_count} nav, {cta_count} CTAs",
            confidence=0.9,
            source="web_scrape",
        )

    def _social_footprint(
        self,
        web: WebData = None,
        exa: ExaData = None,
        social: SocialData = None
    ) -> FeatureValue:
        """
        Social media presence — how many platforms, how active.
        
        Uses SocialData if available, otherwise falls back to web/exa detection.
        """
        # If we have scraped social data, use it for accurate scoring
        if social and social.platforms:
            return self._score_social_from_data(social)
        
        # Fallback: detect platforms from web content and Exa mentions
        platforms_found = []
        
        if web:
            content = web.markdown_content.lower()
            social_platforms = {
                "instagram": ["instagram.com"],
                "twitter": ["twitter.com", "x.com"],
                "linkedin": ["linkedin.com"],
                "facebook": ["facebook.com", "fb.com"],
                "youtube": ["youtube.com", "youtu.be"],
                "tiktok": ["tiktok.com"],
                "github": ["github.com"],
            }

            for platform, domains in social_platforms.items():
                if any(d in content for d in domains):
                    platforms_found.append(platform)

        # Also check Exa mentions for social profiles
        if exa and exa.mentions:
            social_platforms = {
                "instagram": ["instagram.com"],
                "twitter": ["twitter.com", "x.com"],
                "linkedin": ["linkedin.com"],
                "facebook": ["facebook.com", "fb.com"],
                "youtube": ["youtube.com", "youtu.be"],
                "tiktok": ["tiktok.com"],
                "github": ["github.com"],
            }
            for r in exa.mentions:
                for platform, domains in social_platforms.items():
                    if any(d in r.url.lower() for d in domains) and platform not in platforms_found:
                        platforms_found.append(platform)

        score, raw = self._score_discovered_platforms(platforms_found)

        return FeatureValue(
            "social_footprint",
            min(score, 100.0),
            raw_value=raw,
            confidence=0.6,
            source="web_scrape+exa",
        )

    def _score_discovered_platforms(self, platforms_found: list[str]) -> tuple[float, str]:
        """Score platform mix when only inferred public profiles are available."""
        unique_platforms = sorted(set(platforms_found))
        if not unique_platforms:
            return 12.0, "platforms: none"

        weighted_presence = sum(self.PLATFORM_WEIGHTS.get(platform, 0.7) for platform in unique_platforms)
        groups = {self.PLATFORM_GROUPS.get(platform, "social") for platform in unique_platforms}

        score = 18.0 + (weighted_presence * 18.0)
        if "professional" in groups and "builder" in groups:
            score += 8.0
        if len(groups) >= 2:
            score += 6.0
        if len(unique_platforms) >= 3:
            score += 6.0

        raw = (
            f"platforms: {', '.join(unique_platforms)}, "
            f"weighted_presence={weighted_presence:.1f}, "
            f"groups={','.join(sorted(groups))}"
        )
        return min(score, 100.0), raw
    
    def _score_social_from_data(self, social: SocialData) -> FeatureValue:
        """Score social footprint using scraped social data."""
        score = 0.0
        raw_parts = []
        
        # Base score for number of platforms
        num_platforms = len(social.platforms)
        if num_platforms == 0:
            score = 10.0
        elif num_platforms == 1:
            score = 25.0
        elif num_platforms == 2:
            score = 40.0
        elif num_platforms <= 4:
            score = 55.0 + (num_platforms - 2) * 10
        else:
            score = 75.0 + min(num_platforms - 4, 3) * 8
        
        # Bonus for follower counts
        if social.total_followers > 0:
            if social.total_followers >= 1000000:
                score += 20
                raw_parts.append(f"{social.total_followers/1000000:.1f}M followers")
            elif social.total_followers >= 100000:
                score += 15
                raw_parts.append(f"{social.total_followers/1000:.0f}K followers")
            elif social.total_followers >= 10000:
                score += 10
                raw_parts.append(f"{social.total_followers/1000:.1f}K followers")
            elif social.total_followers >= 1000:
                score += 5
                raw_parts.append(f"{social.total_followers} followers")
        
        # Bonus for activity (post frequency)
        if social.avg_post_frequency > 0:
            if social.avg_post_frequency >= 7:  # Daily posting
                score += 5
                raw_parts.append("daily posting")
            elif social.avg_post_frequency >= 1:  # Weekly posting
                score += 3
                raw_parts.append("weekly posting")
        
        # Bonus for verified accounts
        verified_count = sum(1 for m in social.platforms.values() if m.verified)
        if verified_count > 0:
            score += min(verified_count * 3, 10)
            raw_parts.append(f"{verified_count} verified")
        
        # List platforms found
        platform_names = list(social.platforms.keys())
        if not raw_parts:
            raw_parts.append(f"platforms: {', '.join(platform_names)}")
        
        return FeatureValue(
            "social_footprint",
            min(score, 100.0),
            raw_value=" | ".join(raw_parts),
            confidence=0.85,  # Higher confidence with actual scraped data
            source="social_scrape",
        )

    def _search_visibility(self, exa: ExaData = None) -> FeatureValue:
        """
        Does the brand show up in search results?
        This is the BEST proxy for brand strength.
        """
        if not exa or not exa.mentions:
            return FeatureValue("search_visibility", 10.0, confidence=0.5, source="exa")

        num_results = len(exa.mentions)

        # Scale: more results = exponentially stronger brand
        if num_results >= 15:
            score = 95.0
        elif num_results >= 10:
            score = 85.0
        elif num_results >= 7:
            score = 70.0
        elif num_results >= 5:
            score = 55.0
        elif num_results >= 3:
            score = 40.0
        elif num_results >= 1:
            score = 25.0
        else:
            score = 10.0

        # Bonus: brand's own URL in top 3 = very strong signal
        if exa.mentions[:3]:
            brand_lower = exa.brand_name.lower()
            if any(brand_lower in r.url.lower() for r in exa.mentions[:3]):
                score = min(score + 10, 100.0)

        return FeatureValue(
            "search_visibility",
            score,
            raw_value=f"{num_results} results",
            confidence=0.8,
            source="exa",
        )

    def _ai_visibility(self, exa: ExaData = None) -> FeatureValue:
        """Does the brand appear in AI-related content? (proxy for LLM knowledge)"""
        if not exa or not exa.ai_visibility_results:
            return FeatureValue("ai_visibility", 20.0, confidence=0.4, source="exa")

        weighted_sum = 0.0
        strong_results = 0
        medium_results = 0
        for result in exa.ai_visibility_results[:5]:
            relevance = self._normalize_relevance(getattr(result, "score", 0.0))
            subject_relevance = self._subject_relevance(result, exa.brand_name)
            contribution = 30 * relevance * subject_relevance
            weighted_sum += contribution
            if contribution >= 12:
                strong_results += 1
            elif contribution >= 7:
                medium_results += 1

        score = weighted_sum
        if strong_results >= 2:
            score = max(score, 60.0)
        elif strong_results == 1 and medium_results >= 1:
            score = max(score, 55.0)
        elif strong_results == 0 and medium_results >= 2:
            score = max(score, 50.0)
        elif strong_results >= 1:
            score += min(strong_results * 4, 10)

        score = min(score, 100.0)

        return FeatureValue(
            "ai_visibility",
            score,
            raw_value=(
                f"weighted={weighted_sum:.1f}, "
                f"strong_results={strong_results}, "
                f"medium_results={medium_results}, "
                f"total_results={len(exa.ai_visibility_results)}"
            ),
            confidence=0.6,
            source="exa",
        )

    def _directory_listings(self, exa: ExaData = None) -> FeatureValue:
        """Is the brand in relevant directories?"""
        if not exa or not exa.mentions:
            return FeatureValue("directory_listings", 0.0, confidence=0.4, source="exa")

        directories = [
            "crunchbase.com", "linkedin.com/company", "google.com/maps",
            "yelp.com", "glassdoor.com", "trustpilot.com", "g2.com",
            "capterra.com", "angel.co", "producthunt.com",
        ]

        found = 0
        for result in exa.mentions:
            if any(d in result.url.lower() for d in directories):
                found += 1

        score = min(found * 30, 100.0)

        return FeatureValue(
            "directory_listings",
            score,
            raw_value=f"{found} directories found",
            confidence=0.7,
            source="exa",
        )
