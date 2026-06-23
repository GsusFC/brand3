"""Facade for TL;DR brand extractor implementation."""

from __future__ import annotations

from typing import Any

from src.features.magnetism import extractor_impl as _impl
from src.features.magnetism import extractor_runtime_impl as _runtime_impl
from src.features.magnetism.analyst_tldr import (
    maybe_build_system_reading,
    run_analyst_tldr_pass,
)
from src.features.magnetism.extractor_runtime_impl import (  # noqa: F401
    BRAND3_BRAND_RESEARCH_GRAPH_PACK,
    BRAND3_CONTEXTDEV_VISUAL_ENRICHMENT,
    BRAND3_MAGNETISM_RESEARCH_PACK_TLDR,
    build_recommended_research_pack,
)

__all__ = [
    "MagnetismExtractor",
    "maybe_build_system_reading",
    "run_analyst_tldr_pass",
    "BRAND3_MAGNETISM_RESEARCH_PACK_TLDR",
    "BRAND3_BRAND_RESEARCH_GRAPH_PACK",
    "BRAND3_CONTEXTDEV_VISUAL_ENRICHMENT",
    "build_recommended_research_pack",
]


# Re-export legacy tunables so tests patching `src.features.magnetism.extractor.*` keep working
# after the runtime split.
def _sync_extractor_runtime_overrides() -> None:
    """Apply patched facade-level controls into runtime implementation module."""

    _runtime_impl.BRAND3_MAGNETISM_RESEARCH_PACK_TLDR = BRAND3_MAGNETISM_RESEARCH_PACK_TLDR
    _runtime_impl.BRAND3_BRAND_RESEARCH_GRAPH_PACK = BRAND3_BRAND_RESEARCH_GRAPH_PACK
    _runtime_impl.BRAND3_CONTEXTDEV_VISUAL_ENRICHMENT = BRAND3_CONTEXTDEV_VISUAL_ENRICHMENT
    _runtime_impl.build_recommended_research_pack = build_recommended_research_pack


class MagnetismExtractor(_impl.MagnetismExtractor):
    """Compatibility shim for external monkeypatch points."""

    def __init__(
        self,
        llm: Any = None,
        *,
        analyst_llm: Any = None,
        system_reading_llm: Any = None,
    ):
        _sync_extractor_runtime_overrides()
        super().__init__(llm=llm, analyst_llm=analyst_llm, system_reading_llm=system_reading_llm)

    def extract(self, url: str | None = None, manual_text: str | None = None, brand_name: str | None = None):
        _sync_extractor_runtime_overrides()
        return super().extract(url=url, manual_text=manual_text, brand_name=brand_name)

    def extract_from_audit_snapshot(self, snapshot: dict[str, Any]):
        _sync_extractor_runtime_overrides()
        return super().extract_from_audit_snapshot(snapshot)

    @staticmethod
    def _build_research_pack(snapshot: dict[str, Any]):
        _sync_extractor_runtime_overrides()
        return _runtime_impl.MagnetismExtractorRuntimeMixin._build_research_pack(snapshot)

    def _contextdev_candidate_summary_from_snapshot(self, snapshot: dict[str, Any]):
        _sync_extractor_runtime_overrides()
        return super()._contextdev_candidate_summary_from_snapshot(snapshot)

    def _apply_contextdev_visual_enrichment_shadow(
        self,
        *,
        result: dict[str, Any],
        research_pack: Any | None,
        candidate_summary: dict[str, Any] | None,
    ) -> None:
        _sync_extractor_runtime_overrides()
        return super()._apply_contextdev_visual_enrichment_shadow(
            result=result,
            research_pack=research_pack,
            candidate_summary=candidate_summary,
        )

    def _apply_tldr_generation_flow(
        self,
        *,
        result: dict[str, Any],
        brand_name: str,
        url: str,
        packet_dict: dict[str, Any],
        brand_context_brief: dict[str, Any] | None = None,
        research_pack: Any | None = None,
        contextdev_candidate_summary: dict[str, Any] | None = None,
    ) -> None:
        _sync_extractor_runtime_overrides()
        return super()._apply_tldr_generation_flow(
            result=result,
            brand_name=brand_name,
            url=url,
            packet_dict=packet_dict,
            brand_context_brief=brand_context_brief,
            research_pack=research_pack,
            contextdev_candidate_summary=contextdev_candidate_summary,
        )
