"""
Competitor collector for diferenciación scoring.

Discovers competitors via Exa, scrapes their websites via Firecrawl,
and provides comparison utilities for vocabulary, positioning, and features.
"""

import re
import math
from collections import Counter
from dataclasses import dataclass, field

from .exa_collector import ExaCollector, ExaResult, ExaData
from .web_collector import WebCollector, WebData


@dataclass
class CompetitorInfo:
    """A discovered competitor with metadata."""
    name: str
    url: str
    exa_result: ExaResult = None
    web_data: WebData = None
    error: str = ""


@dataclass
class ComparisonResult:
    """Comparison between the brand and a single competitor."""
    competitor_name: str
    competitor_url: str
    keyword_similarity: float = 0.0       # 0-1, Jaccard on keywords
    vocabulary_overlap: float = 0.0        # 0-1, overlap in distinctive terms
    positioning_distance: float = 0.0      # 0-1, how different the positioning language is
    feature_overlap: float = 0.0           # 0-1, overlap in feature/benefit mentions
    overall_distance: float = 0.0          # 0-1, composite distance (higher = more different)
    shared_keywords: list = field(default_factory=list)
    brand_unique_terms: list = field(default_factory=list)
    competitor_unique_terms: list = field(default_factory=list)
    details: str = ""


@dataclass
class CompetitorData:
    """Full competitor analysis for a brand."""
    brand_name: str
    brand_url: str
    competitors: list[CompetitorInfo] = field(default_factory=list)
    comparisons: list[ComparisonResult] = field(default_factory=list)
    brand_web: WebData = None
    errors: list[str] = field(default_factory=list)

    @property
    def avg_distance(self) -> float:
        """Average distance from brand to all competitors (0-1)."""
        if not self.comparisons:
            return 0.5
        return sum(c.overall_distance for c in self.comparisons) / len(self.comparisons)

    @property
    def min_distance(self) -> float:
        """Minimum distance to any competitor (closest competitor)."""
        if not self.comparisons:
            return 0.5
        return min(c.overall_distance for c in self.comparisons)


# Stopwords for keyword extraction
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "and", "but", "or", "nor", "not", "so", "yet",
    "both", "either", "its", "our", "your", "their", "this", "that",
    "these", "it", "we", "you", "they", "he", "she", "i", "me",
    "more", "most", "other", "some", "such", "no", "only", "own",
    "same", "than", "too", "very", "just", "about", "also", "how",
    "what", "when", "where", "which", "who", "whom", "why", "all",
    "each", "every", "few", "here", "there", "then", "once", "if",
    "up", "out", "off", "over", "under", "again", "further", "get",
    "got", "make", "made", "like", "new", "use", "using", "used",
    "see", "need", "based", "including", "without", "within",
}

# Positioning language patterns — how brands frame themselves
_POSITIONING_PATTERNS = [
    r"\bwe (?:are|help|enable|provide|offer|deliver|build|create|make)\b",
    r"\b(?:the|our) (?:first|only|best|leading|premier|ultimate)\b",
    r"\bdesigned (?:for|to)\b",
    r"\bbuilt (?:for|to|by)\b",
    r"\bmade (?:for|to)\b",
    r"\b(?:the|a) (?:better|smarter|faster|easier) (?:way|solution|approach)\b",
    r"\b(?:unlike|different from|compared to)\b",
    r"\bfor (?:teams|businesses|companies|startups|enterprises|creators|developers)\b",
    r"\b(?:one[- ]stop|all[- ]in[- ]one|end[- ]to[- ]end)\b",
    r"\b(?:empower|transform|revolutionize|disrupt|simplify)\b",
]

# Feature/benefit language patterns
_FEATURE_PATTERNS = [
    r"\b(?:real[- ]time|automated?|integrated?|secure|scalable|flexible)\b",
    r"\b(?:api|sdk|dashboard|analytics|reporting|monitoring)\b",
    r"\b(?:free|trial|demo|pricing|plans?)\b",
    r"\b(?:support|onboarding|training|documentation)\b",
    r"\b(?:collaboration|workflow|automation|integration)\b",
    r"\b(?:mobile|cloud|saas|platform|tool|software)\b",
    r"\b(?:ai|machine learning|ml|llm|gpt|neural)\b",
]


def _extract_keywords(text: str, top_n: int = 50) -> set:
    """Extract top keywords from text, excluding stopwords."""
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    words = [w for w in words if w not in _STOPWORDS]
    return set(w for w, _ in Counter(words).most_common(top_n))


def _extract_ngrams(text: str, n: int = 2, top_k: int = 20) -> set:
    """Extract top n-grams from text."""
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    words = [w for w in words if w not in _STOPWORDS]
    ngrams = [' '.join(words[i:i+n]) for i in range(len(words) - n + 1)]
    return set(ng for ng, _ in Counter(ngrams).most_common(top_k))


def _extract_positioning_language(text: str) -> set:
    """Extract positioning phrases from text."""
    text_lower = text.lower()
    found = set()
    for pattern in _POSITIONING_PATTERNS:
        matches = re.findall(pattern, text_lower)
        found.update(matches)
    return found


def _extract_feature_language(text: str) -> set:
    """Extract feature/benefit language from text."""
    text_lower = text.lower()
    found = set()
    for pattern in _FEATURE_PATTERNS:
        matches = re.findall(pattern, text_lower)
        found.update(matches)
    return found


def _jaccard(set_a: set, set_b: set) -> float:
    """Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _cosine_similarity(counter_a: Counter, counter_b: Counter) -> float:
    """Cosine similarity between two term frequency counters."""
    if not counter_a or not counter_b:
        return 0.0
    all_terms = set(counter_a.keys()) | set(counter_b.keys())
    dot = sum(counter_a.get(t, 0) * counter_b.get(t, 0) for t in all_terms)
    norm_a = math.sqrt(sum(v * v for v in counter_a.values()))
    norm_b = math.sqrt(sum(v * v for v in counter_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _extract_term_frequencies(text: str, top_n: int = 100) -> Counter:
    """Extract term frequency counter from text."""
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    words = [w for w in words if w not in _STOPWORDS]
    return Counter(words).most_common(top_n)


def _extract_brand_name_from_url(url: str) -> str:
    """Extract a likely brand name from a URL."""
    domain = re.sub(r'https?://', '', url)
    domain = domain.split('/')[0]
    domain = domain.replace('www.', '')
    name = domain.split('.')[0]
    return name.capitalize()


class CompetitorCollector:
    """
    Discovers competitors, scrapes their websites, and computes
    differentiation metrics for the diferenciación dimension.
    """

    def __init__(self, exa_collector: ExaCollector = None,
                 web_collector: WebCollector = None,
                 max_competitors: int = 5,
                 max_scrape_chars: int = 30000):
        self.exa = exa_collector
        self.web = web_collector
        self.max_competitors = max_competitors
        self.max_scrape_chars = max_scrape_chars

    def collect(self, brand_name: str, brand_url: str,
                brand_web: WebData = None,
                exa_data: ExaData = None) -> CompetitorData:
        """
        Full competitor collection pipeline:
        1. Discover competitors (from Exa data or fresh search)
        2. Scrape competitor websites
        3. Compute comparison metrics
        """
        result = CompetitorData(
            brand_name=brand_name,
            brand_url=brand_url,
            brand_web=brand_web,
        )

        # Step 1: Discover competitors
        competitors = self._discover_competitors(brand_name, brand_url, exa_data)
        result.competitors = competitors[:self.max_competitors]
        print(f"  Competitors: discovered {len(result.competitors)} competitors")

        # Step 2: Scrape competitor websites
        self._scrape_competitors(result)
        scraped = sum(1 for c in result.competitors
                      if c.web_data and not c.web_data.error and c.web_data.markdown_content)
        print(f"  Competitors: scraped {scraped}/{len(result.competitors)} websites")

        # Step 3: Compute comparisons
        if brand_web and brand_web.markdown_content:
            result.comparisons = self._compare_all(brand_web, result.competitors)
            print(f"  Competitors: computed {len(result.comparisons)} comparisons")

        return result

    def _discover_competitors(self, brand_name: str, brand_url: str,
                               exa_data: ExaData = None) -> list[CompetitorInfo]:
        """Discover competitors from Exa data or fresh search."""
        competitors = []
        seen_urls = set()

        # Use existing Exa data if available
        exa_results = []
        if exa_data and exa_data.competitors:
            exa_results = exa_data.competitors

        # If no competitors in existing data, search fresh
        if not exa_results and self.exa:
            try:
                exa_results = self.exa.search(
                    f"competitors alternatives similar to {brand_name}",
                    num_results=self.max_competitors + 5,
                )
            except Exception as e:
                print(f"  Competitor search error: {e}")

        for r in exa_results:
            url = r.url
            # Skip the brand's own domain
            brand_domain = re.sub(r'https?://', '', brand_url).split('/')[0].lower()
            comp_domain = re.sub(r'https?://', '', url).split('/')[0].lower()
            if brand_domain == comp_domain:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            name = r.title or _extract_brand_name_from_url(url)
            # Clean up title (remove " - Company Name" suffixes)
            name = re.split(r'\s*[|\-–—]\s*', name)[0].strip()

            competitors.append(CompetitorInfo(
                name=name,
                url=url,
                exa_result=r,
            ))

        return competitors

    def _scrape_competitors(self, result: CompetitorData):
        """Scrape competitor websites using Firecrawl."""
        if not self.web:
            result.errors.append("No WebCollector available for competitor scraping")
            return

        for comp in result.competitors:
            try:
                web_data = self.web.scrape(comp.url, crawl_subpages=False)
                if web_data and not web_data.error:
                    # Truncate to save memory
                    if len(web_data.markdown_content) > self.max_scrape_chars:
                        web_data.markdown_content = web_data.markdown_content[:self.max_scrape_chars]
                    comp.web_data = web_data
                else:
                    comp.error = web_data.error if web_data else "empty response"
            except Exception as e:
                comp.error = str(e)
                result.errors.append(f"Scrape error for {comp.name}: {e}")

    def _compare_all(self, brand_web: WebData,
                     competitors: list[CompetitorInfo]) -> list[ComparisonResult]:
        """Compare the brand against each competitor."""
        comparisons = []
        brand_content = brand_web.markdown_content

        for comp in competitors:
            if not comp.web_data or not comp.web_data.markdown_content:
                # Use Exa snippet as fallback
                if comp.exa_result and comp.exa_result.text:
                    comp_content = comp.exa_result.text
                else:
                    comparisons.append(ComparisonResult(
                        competitor_name=comp.name,
                        competitor_url=comp.url,
                        overall_distance=0.5,
                        details="no competitor content available",
                    ))
                    continue
            else:
                comp_content = comp.web_data.markdown_content

            comparison = self._compare_pair(brand_content, comp_content,
                                            comp.name, comp.url)
            comparisons.append(comparison)

        return comparisons

    def _compare_pair(self, brand_text: str, comp_text: str,
                      comp_name: str, comp_url: str) -> ComparisonResult:
        """
        Deep comparison between brand and competitor text.
        Computes multiple distance metrics.
        """
        # 1. Keyword similarity (Jaccard on top keywords)
        brand_kw = _extract_keywords(brand_text)
        comp_kw = _extract_keywords(comp_text)
        keyword_sim = _jaccard(brand_kw, comp_kw)

        # 2. Bigram overlap (catches phrases like "machine learning", "real time")
        brand_bi = _extract_ngrams(brand_text, n=2)
        comp_bi = _extract_ngrams(comp_text, n=2)
        bigram_sim = _jaccard(brand_bi, comp_bi)

        # 3. Positioning language similarity
        brand_pos = _extract_positioning_language(brand_text)
        comp_pos = _extract_positioning_language(comp_text)
        positioning_sim = _jaccard(brand_pos, comp_pos)

        # 4. Feature/benefit language similarity
        brand_feat = _extract_feature_language(brand_text)
        comp_feat = _extract_feature_language(comp_text)
        feature_sim = _jaccard(brand_feat, comp_feat)

        # 5. Cosine similarity on term frequencies (broader vocabulary comparison)
        brand_tf = Counter(dict(_extract_term_frequencies(brand_text)))
        comp_tf = Counter(dict(_extract_term_frequencies(comp_text)))
        cosine_sim = _cosine_similarity(brand_tf, comp_tf)

        # Composite distance: weighted average of all metrics
        # Higher distance = more differentiated = better for the brand
        overall_dist = 1.0 - (
            keyword_sim * 0.20 +
            bigram_sim * 0.15 +
            positioning_sim * 0.25 +
            feature_sim * 0.15 +
            cosine_sim * 0.25
        )

        # Unique/shared terms for insights
        shared = sorted(brand_kw & comp_kw)
        brand_unique = sorted(brand_kw - comp_kw)[:15]
        comp_unique = sorted(comp_kw - brand_kw)[:15]

        return ComparisonResult(
            competitor_name=comp_name,
            competitor_url=comp_url,
            keyword_similarity=round(keyword_sim, 3),
            vocabulary_overlap=round(bigram_sim, 3),
            positioning_distance=round(1.0 - positioning_sim, 3),
            feature_overlap=round(feature_sim, 3),
            overall_distance=round(overall_dist, 3),
            shared_keywords=shared[:20],
            brand_unique_terms=brand_unique,
            competitor_unique_terms=comp_unique,
            details=f"kw={keyword_sim:.2f} bi={bigram_sim:.2f} "
                    f"pos={positioning_sim:.2f} feat={feature_sim:.2f} "
                    f"cos={cosine_sim:.2f}",
        )
