from __future__ import annotations

LAYER_KEYS = [
    "mindspace",
    "aetherspace",
    "gamespace",
    "envispace",
    "netspace",
    "tactispace",
    "ambientspace",
]

LAYER_DEFINITIONS = {
    "mindspace": {
        "question": "Which",
        "description": "central emotion, mantra, war cry, or magnetic phrase",
        "tldr": ["magnetism"],
    },
    "aetherspace": {
        "question": "Why",
        "description": "purpose beyond the product",
        "tldr": ["core_purpose"],
    },
    "gamespace": {
        "question": "Who",
        "description": "brand personality and archetype",
        "tldr": ["personality"],
    },
    "envispace": {
        "question": "How",
        "description": "visual and conceptual brand idea",
        "tldr": ["brand_idea"],
    },
    "netspace": {
        "question": "When",
        "description": "concrete value proposition and exchange of value",
        "tldr": ["value_proposition"],
    },
    "tactispace": {
        "question": "Where",
        "description": "mission and vision signals",
        "tldr": ["mission", "vision"],
    },
    "ambientspace": {
        "question": "What",
        "description": "values and attributes demonstrated in context",
        "tldr": ["attributes", "values"],
    },
}

TLDR_KEYS = [
    "core_purpose",
    "magnetism",
    "value_proposition",
    "personality",
    "brand_idea",
    "attributes",
    "values",
    "mission",
    "vision",
]

LAYER_TO_TLDR = {
    "aetherspace": ["core_purpose"],
    "mindspace": ["magnetism"],
    "netspace": ["value_proposition"],
    "gamespace": ["personality"],
    "envispace": ["brand_idea"],
    "ambientspace": ["attributes", "values"],
    "tactispace": ["mission", "vision"],
}

TLDR_TO_LAYER = {
    block: layer for layer, blocks in LAYER_TO_TLDR.items() for block in blocks
}

TLDR_BLOCK_CONTRACT = {
    "core_purpose": {
        "question": "Why does this brand appear to exist beyond the product?",
        "evidence_scope": ["aetherspace", "mindspace", "ambientspace"],
        "source_signal": "Essence",
        "source_signal_path": "Essence → Core Purpose",
        "source_layer": "aetherspace",
    },
    "magnetism": {
        "question": "What phrase or tension best concentrates the brand's magnetic energy?",
        "evidence_scope": ["mindspace", "netspace", "aetherspace"],
        "source_signal": "Emotions",
        "source_signal_path": "Emotions → Magnetism",
        "source_layer": "mindspace",
    },
    "value_proposition": {
        "question": "What does the brand offer, to whom, and what changes for that audience?",
        "evidence_scope": ["netspace", "tactispace", "ambientspace"],
        "source_signal": "Exchange",
        "source_signal_path": "Exchange → Value Proposition",
        "source_layer": "netspace",
    },
    "personality": {
        "question": "What personality does the brand perform through tone, vocabulary, behavior, and visual expression?",
        "evidence_scope": ["gamespace", "mindspace", "netspace", "ambientspace"],
        "source_signal": "Voice",
        "source_signal_path": "Voice → Personality",
        "source_layer": "gamespace",
    },
    "brand_idea": {
        "question": "What conceptual idea connects strategy, category, and expression?",
        "evidence_scope": ["envispace", "mindspace", "aetherspace", "netspace"],
        "source_signal": "Expression",
        "source_signal_path": "Expression → Brand Idea",
        "source_layer": "envispace",
    },
    "attributes": {
        "question": "Which three attributes does the brand describe or demonstrate consistently?",
        "evidence_scope": ["ambientspace", "netspace", "mindspace"],
        "source_signal": "Context / Beliefs",
        "source_signal_path": "Context / Beliefs → Attributes",
        "source_layer": "ambientspace",
    },
    "values": {
        "question": "Which three values does the brand appear to defend through what it says and does?",
        "evidence_scope": ["ambientspace", "aetherspace", "tactispace"],
        "source_signal": "Context / Beliefs",
        "source_signal_path": "Context / Beliefs → Values",
        "source_layer": "ambientspace",
    },
    "mission": {
        "question": "What does the brand concretely do today?",
        "evidence_scope": ["tactispace", "netspace", "aetherspace"],
        "source_signal": "Action / Direction",
        "source_signal_path": "Action / Direction → Mission",
        "source_layer": "tactispace",
    },
    "vision": {
        "question": "What future or category change does the brand appear to be building toward?",
        "evidence_scope": ["tactispace", "aetherspace", "mindspace"],
        "source_signal": "Action / Direction",
        "source_signal_path": "Action / Direction → Vision",
        "source_layer": "tactispace",
    },
}

STRATEGIC_TLDR_BLOCKS = {"core_purpose", "personality", "brand_idea", "values", "vision"}
PERFORMED_TLDR_BLOCKS = {"personality", "attributes", "values"}
DECLARATIVE_TLDR_BLOCKS = {"core_purpose", "magnetism", "value_proposition", "mission"}

GENERIC_MAGNETISM_TERMS = {
    "empower",
    "empowering",
    "future",
    "innovation",
    "innovative",
    "transform",
    "transforming",
    "leverage",
    "leading",
    "platform",
    "solution",
    "seamless",
    "unlock",
    "elevate",
}

SPECIFICITY_TERMS = {
    "api",
    "ai",
    "athlete",
    "athletes",
    "wealth",
    "banking",
    "developer",
    "protocol",
    "capital",
    "data",
    "security",
    "compliance",
    "automation",
    "workflow",
    "infrastructure",
    "advisors",
    "founders",
    "teams",
    "marathon",
    "maraton",
    "performance",
    "sport",
    "sports",
    "training",
}
