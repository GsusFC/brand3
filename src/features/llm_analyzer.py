"""
LLM-based brand analysis.

Uses LLM to make subjective judgments that keyword matching can't:
- Is the brand's language unique or generic?
- What category/positioning does the brand claim?
- How does third-party perception compare to self-description?
- What are the brand's distinctive concepts?

Provider is configured via src.config (OpenAI-compatible API).
"""

import json
import urllib.request
import urllib.error

from src.config import BRAND3_LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


class LLMAnalyzer:
    """LLM-powered brand content analyzer."""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or BRAND3_LLM_API_KEY
        self.base_url = base_url or LLM_BASE_URL
        self.model = model or LLM_MODEL

    def _call(self, system: str, user: str, max_tokens: int = 1000) -> str:
        """Make an LLM call via Nous API."""
        if not self.api_key:
            return ""

        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                msg = data["choices"][0]["message"]
                content = msg.get("content") or ""
                # Some reasoning models put response in reasoning field when content is null
                if not content:
                    content = msg.get("reasoning") or ""
                return content
        except Exception as e:
            print(f"  LLM call failed: {e}")
            return ""

    def _call_json(self, system: str, user: str) -> dict:
        """Make an LLM call expecting JSON response."""
        response = self._call(system, user, max_tokens=800)
        if not response:
            return {}

        # Try to extract JSON from response (might have markdown wrapping)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {}

    def analyze_positioning(self, web_content: str, brand_name: str) -> dict:
        """
        What category/positioning does the brand claim?
        Returns: {category, value_prop, target_audience, key_messages, distinctive_concepts, positioning_clarity}
        """
        # Truncate content for LLM
        content = web_content[:3000]

        return self._call_json(
            system="You are a brand analyst. Analyze the brand's positioning from its website content. Return ONLY valid JSON.",
            user=f"""Analyze this brand's positioning from their website.

Brand: {brand_name}
Website content:
---
{content}
---

Return JSON with this exact structure:
{{
    "category": "what category/type of company they claim to be (e.g. 'payments infrastructure', 'project management tool')",
    "value_prop": "their core value proposition in one sentence",
    "target_audience": "who they're targeting (e.g. 'developers', 'enterprise teams', 'small businesses')",
    "key_messages": ["list", "of", "their", "main", "messages"],
    "distinctive_concepts": ["any unique terms", "or concepts they", "invented or popularized"],
    "positioning_clarity": 0-100
}}"""
        )

    def analyze_differentiation(self, web_content: str, brand_name: str,
                                 competitor_content: str = "") -> dict:
        """
        Is the brand saying something DIFFERENT from competitors?
        Returns: {uniqueness_score, generic_phrases, unique_phrases, positioning_clarity}
        """
        content = web_content[:2500]
        comp_section = f"\n\nCompetitor context:\n{competitor_content[:1000]}" if competitor_content else ""

        return self._call_json(
            system="You are a brand differentiation analyst. Score how unique vs generic a brand's messaging is. Return ONLY valid JSON.",
            user=f"""Analyze how differentiated this brand's messaging is.

Brand: {brand_name}
Website content:
---
{content}
---{comp_section}

Evaluate:
1. How much of their language is generic marketing speak vs specific/unique?
2. Do they articulate a clear, distinctive positioning?
3. Do they have their own vocabulary/concepts?

Return JSON:
{{
    "uniqueness_score": 0-100 (0=completely generic, 100=highly unique and distinctive),
    "generic_phrases": ["list of generic phrases found"],
    "unique_phrases": ["list of distinctive/original phrases"],
    "positioning_clarity": 0-100 (how clearly they articulate what makes them different),
    "reasoning": "brief explanation of the score"
}}"""
        )

    def analyze_sentiment(self, mentions: list[str], brand_name: str) -> dict:
        """
        Analyze sentiment from third-party mentions.
        Returns: {overall_sentiment, key_themes, positive_signals, negative_signals}
        """
        mentions_text = "\n---\n".join(mentions[:10])

        return self._call_json(
            system="You are a brand perception analyst. Analyze sentiment from mentions about a brand. Return ONLY valid JSON.",
            user=f"""Analyze the sentiment and perception of {brand_name} based on these mentions:

---
{mentions_text}
---

Return JSON:
{{
    "overall_sentiment": "positive" | "neutral" | "negative" | "mixed",
    "sentiment_score": 0-100 (0=very negative, 50=neutral, 100=very positive),
    "key_themes": ["main topics people discuss about this brand"],
    "positive_signals": ["specific positive things mentioned"],
    "negative_signals": ["specific negative things mentioned"],
    "controversy_detected": true/false,
    "controversy_details": "description if any, null otherwise"
}}"""
        )

    def analyze_coherence(self, web_content: str, third_party_descriptions: list[str],
                           brand_name: str) -> dict:
        """
        Does the brand describe itself consistently with how others describe it?
        Returns: {alignment_score, self_description, third_party_description, gaps}
        """
        content = web_content[:2000]
        third_text = "\n---\n".join(third_party_descriptions[:5])

        return self._call_json(
            system="You are a brand coherence analyst. Compare how a brand describes itself vs how others describe it. Return ONLY valid JSON.",
            user=f"""Compare how {brand_name} describes itself vs how third parties describe it.

Brand's own website:
---
{content}
---

Third-party descriptions:
---
{third_text}
---

Return JSON:
{{
    "alignment_score": 0-100 (how well aligned are self-perception and external perception),
    "self_category": "what the brand says it is",
    "third_party_category": "what others say it is",
    "aligned_messages": ["topics where both agree"],
    "gaps": ["areas where self-description and external perception differ"],
    "reasoning": "brief explanation"
}}"""
        )
