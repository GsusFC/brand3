"""Executable TLDR Brand3 block interpreter specs.

The specs define the exercise each migrated TLDR block must perform. Runtime
logic still lives in ``extractor.py`` for now; this module keeps the method
contract separate from scanner orchestration so specs can evolve independently.
"""

from __future__ import annotations

from typing import Any


TLDR_BLOCK_INTERPRETER_SPECS = {
    "value_proposition": {
        "block": "value_proposition",
        "task": "Identify the concrete value exchange: offer, audience, and change.",
        "primary_question": "What does the brand offer, to whom, and what changes for that audience?",
        "source_layers": ["netspace", "tactispace", "ambientspace"],
        "strategic_groups": ["product_offer", "audience", "outcome", "hero_claims"],
        "look_for": [
            "offer", "offers", "solution", "solutions", "platform", "product", "service", "services",
            "api", "system", "management", "streamline", "centralise", "centralize", "reconcile",
            "execute", "forecast", "payments", "pagos", "billing", "facturación", "financial services",
            "servicios financieros", "revenue", "ingresos", "product development", "planning and building",
            "teams and agents", "human intelligence", "business analyst", "research people",
            "research people and companies", "soluciones", "materias primas", "ingredientes", "biorremediación",
            "cosmética", "nutrición",
        ],
        "reject": ["main menu", "contacto", "subscribe now", "buy now", "book a demo"],
        "minimum_evidence_rule": "At least one concrete offer or service description.",
        "claim_type_rules": "declared when the offer is directly stated; inferred only when features imply the offer.",
        "mode_rules": "compressed for direct offer evidence; needs_human_review when audience or outcome is unclear.",
        "confidence_rules": "high requires offer plus outcome; medium requires clear offer; low is inferred from sparse features.",
        "human_review_triggers": ["missing_audience", "missing_outcome", "multiple_offers"],
        "output_style": "Concrete functional offer; avoid category slogans.",
    },
    "mission": {
        "block": "mission",
        "task": "Identify the brand's current operating activity.",
        "primary_question": "What does the brand concretely do today?",
        "source_layers": ["tactispace", "netspace", "aetherspace"],
        "strategic_groups": ["mission_language"],
        "look_for": [
            "we build", "we create", "we provide", "we offer", "we operate", "we deliver",
            "builds", "creates", "provides", "offers", "operates", "delivers", "help", "helps",
            "creamos", "construimos", "ofrecemos", "proporcionamos", "desarrollamos",
        ],
        "reject": [
            "contact us", "book a demo", "subscribe", "buy now", "pricing", "future", "futuro",
            "vision", "visión", "new model", "nuevo modelo",
        ],
        "minimum_evidence_rule": "At least one concrete present-tense operating claim.",
        "claim_type_rules": "declared when copied/compressed from an operating claim; inferred only from clear product/service evidence.",
        "mode_rules": "compressed for direct operating evidence; not_detected for CTAs, slogans, or future language.",
        "confidence_rules": "high requires explicit mission/current activity; medium requires clear operating claim; low is inferred from product evidence only.",
        "human_review_triggers": ["inferred_from_product_only", "mission_vision_mixed"],
        "output_style": "Concrete, present-tense, operational. No aspiration.",
    },
    "vision": {
        "block": "vision",
        "task": "Identify the future state, category shift, or long-term change.",
        "primary_question": "What future, category shift, or change does the brand appear to be building toward?",
        "source_layers": ["tactispace", "aetherspace", "mindspace"],
        "strategic_groups": ["vision_language"],
        "look_for": [
            "future", "future of", "vision", "new model", "new paradigm", "transform", "towards",
            "toward", "redefine", "next generation", "futuro", "visión", "nuevo modelo",
            "nuevo paradigma", "transformar",
        ],
        "reject": ["we build", "we create", "we provide", "creamos", "ofrecemos", "book a demo", "pricing"],
        "minimum_evidence_rule": "At least one future-facing or category-change signal.",
        "claim_type_rules": "declared when the brand states a vision; inferred when Brand3 articulates a future hypothesis from future-facing evidence.",
        "mode_rules": "interpreted_from_discourse for future signals that need articulation; not_detected without future/category-change evidence.",
        "confidence_rules": "high requires explicit vision plus support; medium requires clear future/category-change signal; low is weak future language.",
        "human_review_triggers": ["future_from_current_offer_only", "generic_transform_language", "mission_vision_overlap"],
        "output_style": "Future-oriented but bounded. Avoid grandiose category claims unless explicit.",
    },
}


def get_tldr_block_interpreter_spec(block: str) -> dict[str, Any] | None:
    """Return the executable spec for a migrated TLDR block."""
    spec = TLDR_BLOCK_INTERPRETER_SPECS.get(block)
    return dict(spec) if spec else None
