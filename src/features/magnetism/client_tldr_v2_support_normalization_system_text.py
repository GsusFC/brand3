"""Shared block text mappings for TLDR v2 normalization."""

from __future__ import annotations


def _question_for_block(key: str, language: str) -> str:
    questions = {
        "core_purpose": {
            "en": "What is the clearest visible purpose behind the brand?",
            "es": "¿Cuál es el propósito visible más claro detrás de la marca?",
        },
        "magnetism": {
            "en": "What phrase or tension is most memorable here?",
            "es": "¿Qué frase o tensión resulta más memorable aquí?",
        },
        "value_proposition": {
            "en": "What changes for the audience when they choose this brand?",
            "es": "¿Qué cambia para la audiencia cuando elige esta marca?",
        },
        "personality": {
            "en": "What personality is actually visible in the brand's voice and behavior?",
            "es": "¿Qué personalidad es realmente visible en la voz y el comportamiento de la marca?",
        },
        "brand_idea": {
            "en": "What concept connects the offer, the expression, and the metaphor?",
            "es": "¿Qué concepto conecta la oferta, la expresión y la metáfora?",
        },
        "attributes": {
            "en": "Which attributes are truly repeated across the evidence?",
            "es": "¿Qué atributos se repiten de verdad en la evidencia?",
        },
        "values": {
            "en": "Which values are defended through behavior rather than declared only in words?",
            "es": "¿Qué valores se defienden con comportamiento y no solo con palabras?",
        },
        "mission": {
            "en": "What does the brand concretely do today?",
            "es": "¿Qué hace concretamente la marca hoy?",
        },
        "vision": {
            "en": "What future shift is the brand trying to make visible?",
            "es": "¿Qué cambio futuro intenta hacer visible la marca?",
        },
    }
    return questions.get(key, {}).get(language, questions.get(key, {}).get("en", ""))


def _block_label(key: str, language: str) -> str:
    labels = {
        "core_purpose": {"en": "Core purpose", "es": "Propósito central"},
        "magnetism": {"en": "Magnetism", "es": "Magnetismo"},
        "value_proposition": {"en": "Value proposition", "es": "Propuesta de valor"},
        "personality": {"en": "Personality", "es": "Personalidad"},
        "brand_idea": {"en": "Brand idea", "es": "Idea de marca"},
        "attributes": {"en": "Attributes", "es": "Atributos"},
        "values": {"en": "Values", "es": "Valores"},
        "mission": {"en": "Mission", "es": "Misión"},
        "vision": {"en": "Vision", "es": "Visión"},
    }
    return labels.get(key, {}).get(language, labels.get(key, {}).get("en", key))
