"""
Coherencia feature extractor — LLM-powered.

Uses LLM to compare brand self-description vs third-party perception.
Falls back to heuristic if LLM fails.
"""

from ..models.brand import FeatureValue
from ..collectors.web_collector import WebData
from ..collectors.exa_collector import ExaData
from .llm_analyzer import LLMAnalyzer
from .coherencia import CoherenciaExtractor
from .visual_analyzer import VisualAnalyzer


class CoherenciaLLMExtractor(CoherenciaExtractor):
    """LLM-enhanced coherencia extractor."""

    def __init__(
        self,
        llm: LLMAnalyzer = None,
        visual_analyzer: VisualAnalyzer = None,
        skip_visual_analysis: bool = False,
    ):
        super().__init__(
            visual_analyzer=visual_analyzer,
            skip_visual_analysis=skip_visual_analysis,
        )
        self.llm = llm or LLMAnalyzer()

    def extract(self, web: WebData = None, exa: ExaData = None) -> dict[str, FeatureValue]:
        # Start with heuristic features
        features = super().extract(web, exa)

        if not web or web.error or not self.llm.api_key:
            return features

        # ── LLM: Coherence analysis ──
        print("  [LLM] Analyzing brand coherence...")
        third_party = []
        if exa and exa.mentions:
            third_party = [
                ((r.text or "") + " " + (r.title or ""))[:300]
                for r in exa.mentions[:5]
            ]

        coherence = self.llm.analyze_coherence(
            web.markdown_content, third_party,
            exa.brand_name if exa else "unknown"
        )

        if coherence:
            alignment = coherence.get("alignment_score", 50)

            # Override messaging_consistency with LLM judgment
            features["messaging_consistency"] = FeatureValue(
                "messaging_consistency",
                alignment,
                raw_value=f"self: {coherence.get('self_category', '?')}, "
                          f"third_party: {coherence.get('third_party_category', '?')}, "
                          f"gaps: {coherence.get('gaps', [])[:2]}",
                confidence=0.85,
                source="llm",
            )

        return features
