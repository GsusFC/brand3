"""Scoring and scoring-adjacent derivation helpers for `MagnetismExtractor`."""

from __future__ import annotations

from typing import Any

from src.features.magnetism.extractor_scoring import (
    derive_diagnosis as _scoring_derive_diagnosis,
    derive_metrics as _scoring_derive_metrics,
    earned_magnetism_adjustment as _scoring_earned_magnetism_adjustment,
    magnetism_phrase_breakdown as _scoring_magnetism_phrase_breakdown,
)
from src.features.magnetism.extractor_system_reading import (
    derive_system_reading as _system_reading_derive_system_reading,
)
from src.features.magnetism.extractor_tail import (
    clamp as _tail_clamp,
    absence_of_contradiction_score as _tail_absence_of_contradiction_score,
    int_between as _tail_int_between,
    normalized_tldr_confidence as _tail_normalized_tldr_confidence,
    weighted_score as _tail_weighted_score,
)


class MagnetismExtractorDerivationScoringMixin:
    """Scoring helpers for TLDR metrics and diagnosis."""

    def _derive_metrics(
        self,
        layers: dict[str, Any],
        tldr: dict[str, Any],
        *,
        scoring_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _scoring_derive_metrics(
            layers,
            tldr,
            scoring_context=scoring_context,
            int_between_fn=_tail_int_between,
            earned_magnetism_adjustment_fn=self._earned_magnetism_adjustment,
            semantic_alignment_score_fn=self._semantic_alignment_score,
            absence_of_contradiction_score_fn=self._absence_of_contradiction_score,
            weighted_score_fn=_tail_weighted_score,
        )

    def _derive_diagnosis(self, layers: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
        return _scoring_derive_diagnosis(layers, metrics)

    @staticmethod
    def _earned_magnetism_adjustment(
        expressive_score: int,
        scoring_context: dict[str, Any] | None,
        *,
        clamp_fn=None,
        int_between_fn=None,
    ) -> dict[str, Any]:
        clamp = clamp_fn or MagnetismExtractorDerivationScoringMixin._clamp
        int_between = int_between_fn or MagnetismExtractorDerivationScoringMixin._int_between
        return _scoring_earned_magnetism_adjustment(
            expressive_score,
            scoring_context,
            clamp_fn=clamp,
            int_between_fn=int_between,
        )

    @staticmethod
    def _semantic_alignment_score(layers: dict[str, Any], clamp_fn=None) -> int:
        from src.features.magnetism.extractor_tail import semantic_alignment_score as _tail_semantic_alignment_score

        score = _tail_semantic_alignment_score(layers)
        return clamp_fn(score) if callable(clamp_fn) else score

    @staticmethod
    def _absence_of_contradiction_score(tldr: dict[str, Any], clamp_fn=None) -> int:
        score = _tail_absence_of_contradiction_score(tldr)
        return clamp_fn(score) if callable(clamp_fn) else score

    @staticmethod
    def _clamp(value: int | float) -> int:
        return _tail_clamp(value)

    @staticmethod
    def _int_between(value: Any, minimum: int, maximum: int) -> int | None:
        return _tail_int_between(value, minimum, maximum)

    @staticmethod
    def _derive_system_reading(
        tldr: dict[str, Any],
        layers: dict[str, Any],
        metrics: dict[str, Any],
        evidence_packet_summary: dict[str, Any] | None = None,
        url: str = "",
        brand_name: str = "Unknown Brand",
    ) -> dict[str, Any]:
        return _system_reading_derive_system_reading(
            tldr=tldr,
            layers=layers,
            metrics=metrics,
            evidence_packet_summary=evidence_packet_summary,
            url=url,
            brand_name=brand_name,
        )

    @staticmethod
    def _normalize_tldr_confidence(value: Any, detected: bool) -> str:
        return _tail_normalized_tldr_confidence(value, detected)

    @staticmethod
    def _magnetism_phrase_breakdown(text: str) -> dict[str, int]:
        return _scoring_magnetism_phrase_breakdown(text)
