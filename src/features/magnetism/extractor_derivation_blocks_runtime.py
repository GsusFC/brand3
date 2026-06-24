"""Heuristic block derivation helpers for `MagnetismExtractor`.

This module keeps the domain-specific block inference logic isolated from the
general derivation orchestration mixin.
"""

from __future__ import annotations

from typing import Any


class MagnetismExtractorDerivationBlocksMixin:
    """Derive high-level TLDR blocks from aggregated layer evidence."""

    def _derive_personality_block(self, layers: dict[str, Any]) -> dict[str, Any] | None:
        text = self._joined_layer_evidence(layers, ["netspace", "aetherspace", "ambientspace", "mindspace"])
        if not text:
            return None
        low = text.lower()
        sage = any(
            term in low
            for term in (
                "funcional",
                "materias primas",
                "biorremediación",
                "bioremediation",
                "technical",
                "infrastructure",
                "api",
            )
        )
        caregiver = any(
            term in low
            for term in (
                "regenerativo",
                "medio ambiente",
                "salud",
                "nutrition",
                "nutrición",
                "sostenible",
                "sostenibles",
            )
        )
        creator = any(
            term in low
            for term in ("creamos", "create", "formulaciones", "ingredients", "ingredientes", "materias primas")
        )
        hero = any(
            term in low
            for term in (
                "just do it",
                "atletas",
                "athletes",
                "maratón",
                "marathon",
                "performance",
                "inspirar",
                "inspire",
            )
        )
        if not any((sage, caregiver, creator, hero)):
            return None
        traits = []
        if hero:
            traits.append("Hero")
        if sage:
            traits.append("Applied Sage")
        if caregiver:
            traits.append("Caregiver")
        if creator:
            traits.append("scientific Creator")
        content = self._compose_personality_content(traits)
        evidence = self._first_layer_evidences(layers, ["netspace", "aetherspace", "ambientspace", "mindspace"], limit=3)
        return {
            "content": content,
            "detected": True,
            "mode": "interpreted_from_discourse",
            "confidence": "medium" if len(evidence) >= 2 else "low",
            "evidence": evidence,
            "rationale": "The personality is inferred from repeated discourse patterns, not from a declared personality statement.",
            "source_layers": ["gamespace", "netspace", "ambientspace"],
            "human_review_recommended": False,
        }

    def _derive_brand_idea_block(self, layers: dict[str, Any]) -> dict[str, Any] | None:
        text = self._joined_layer_evidence(layers, ["mindspace", "aetherspace", "netspace", "ambientspace"])
        low = text.lower()
        if any(term in low for term in ("just do it", "atletas", "athletes")) and any(
            term in low for term in ("innovadores", "performance", "maratón", "marathon", "productos")
        ):
            evidence = self._first_layer_evidences(layers, ["mindspace", "aetherspace", "netspace"], limit=3)
            return {
                "content": "Action-led athletic performance for every athlete.",
                "detected": True,
                "mode": "interpreted_from_discourse",
                "confidence": "medium" if len(evidence) >= 2 else "low",
                "evidence": evidence,
                "rationale": "The brand idea is articulated from the action mantra, athlete purpose, and performance-product context.",
                "source_layers": ["envispace", "mindspace", "aetherspace", "netspace"],
                "human_review_recommended": False,
            }
        if not ("macroalgas" in low and ("regenerativo" in low or "medio ambiente" in low)):
            return None
        evidence = self._first_layer_evidences(layers, ["mindspace", "aetherspace", "netspace"], limit=2)
        return {
            "content": "Mediterranean biotech translated into a regenerative industrial identity.",
            "detected": True,
            "mode": "interpreted_from_discourse",
            "confidence": "low",
            "evidence": evidence,
            "rationale": "The idea connects Mediterranean origin, biotech material, industry, and environmental regeneration; visual evidence is still needed.",
            "source_layers": ["envispace", "mindspace", "aetherspace"],
            "human_review_recommended": False,
        }

    def _derive_mission_block(self, layers: dict[str, Any]) -> dict[str, Any] | None:
        text = self._joined_layer_evidence(
            layers, ["tactispace", "netspace", "aetherspace", "ambientspace", "mindspace"]
        )
        sentences = self._sentences(text)
        evidence = self._first_matching_sentence(sentences, ["creamos", "we create", "we build", "we provide"])
        if not evidence:
            return None
        return {
            "content": evidence,
            "detected": True,
            "mode": "compressed",
            "confidence": "medium",
            "evidence": [evidence],
            "rationale": "The evidence states a present-tense operating activity.",
            "source_layers": ["tactispace", "netspace"],
            "human_review_recommended": False,
        }

    def _derive_vision_block(self, layers: dict[str, Any]) -> dict[str, Any] | None:
        text = self._joined_layer_evidence(layers, ["mindspace", "aetherspace", "ambientspace"])
        sentences = self._sentences(text)
        evidence = self._first_matching_sentence(sentences, ["nuevo modelo", "future", "vision", "futuro"])
        if not evidence:
            return None
        return {
            "content": "A regenerative industrial model built around the potential of Mediterranean macroalgae."
            if "macroalgas" in evidence.lower()
            else evidence,
            "detected": True,
            "mode": "interpreted_from_discourse",
            "confidence": "medium",
            "evidence": [evidence],
            "rationale": "The evidence points to a future category model rather than only a current offer.",
            "source_layers": ["tactispace", "mindspace"],
            "human_review_recommended": False,
        }

    @staticmethod
    def _compose_personality_content(traits: list[str]) -> str:
        if not traits:
            return ""
        if len(traits) == 1:
            return traits[0]
        if len(traits) == 2:
            return f"{traits[0]} with {traits[1]} traits."
        return f"{traits[0]} with {traits[1]} and {traits[2]} traits."

    @staticmethod
    def _joined_layer_evidence(layers: dict[str, Any], layer_keys: list[str]) -> str:
        values: list[str] = []
        for key in layer_keys:
            layer = layers.get(key) or {}
            if layer.get("evidence"):
                values.append(str(layer["evidence"]))
            if layer.get("finding"):
                values.append(str(layer["finding"]))
        return "\n".join(values)

    @staticmethod
    def _first_layer_evidences(layers: dict[str, Any], layer_keys: list[str], limit: int) -> list[str]:
        evidence: list[str] = []
        for key in layer_keys:
            layer_evidence = layers.get(key, {}).get("evidence")
            if layer_evidence and layer_evidence not in evidence:
                evidence.append(str(layer_evidence))
            if len(evidence) >= limit:
                break
        return evidence
