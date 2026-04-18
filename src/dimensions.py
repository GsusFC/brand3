"""
Dimension and feature definitions for Brand3 Scoring.

Each dimension has:
- weight: importance in composite score (sums to 1.0)
- features: what we measure, each with its own weight within the dimension
- rules: heuristic overrides that can cap or boost scores
"""

DIMENSIONS = {

    "coherencia": {
        "description": "¿El messaging, visual y tono son consistentes across touchpoints?",
        "weight": 0.20,
        "features": {
            "visual_consistency": {
                "description": "¿Colores, tipografía e imágenes son consistentes? (AI-vision)",
                "weight": 0.25,
                "sources": ["web_scrape", "visual_analysis"],
            },
            "messaging_consistency": {
                "description": "¿Cómo se describe la marca vs cómo la describen terceros? Juicio LLM con citas literales",
                "weight": 0.40,
                "sources": ["web_scrape", "exa", "llm_analysis"],
            },
            "tone_consistency": {
                "description": "¿El tono de la web coincide con el tono de cómo hablan de ella? Juicio LLM",
                "weight": 0.20,
                "sources": ["web_scrape", "exa", "llm_analysis"],
            },
            "cross_channel_coherence": {
                "description": "¿Links a socials, contact, touchpoints, y mentions externas al propio dominio?",
                "weight": 0.15,
                "sources": ["web_scrape", "exa"],
            },
        },
        "rules": [
            "si no tiene web propia → cap a 40",
            "si solo tiene 1 canal activo → cap a 50",
        ],
    },

    "presencia": {
        "description": "¿Dónde aparece la marca y cuánta descubrilidad real tiene?",
        "weight": 0.20,
        "features": {
            "web_presence": {
                "description": "¿Tiene web propia real, segura y con identidad reconocible?",
                "weight": 0.30,
                "sources": ["web_scrape"],
            },
            "social_footprint": {
                "description": "Presencia y actividad social en plataformas relevantes",
                "weight": 0.35,
                "sources": ["social_media"],
            },
            "search_visibility": {
                "description": "Descubribilidad en búsqueda y visibilidad en resultados de IA",
                "weight": 0.25,
                "sources": ["exa", "llm_probe"],
            },
            "directory_presence": {
                "description": "Presencia en directorios estructurados y plataformas de listing",
                "weight": 0.10,
                "sources": ["exa"],
            },
        },
        "rules": [
            "si no tiene web ni socials → score directo 5 (marca fantasma)",
        ],
    },

    "percepcion": {
        "description": "¿Qué sentiment genera? ¿Cómo hablan de ella?",
        "weight": 0.25,
        "features": {
            "brand_sentiment": {
                "description": "Juicio LLM del sentimiento público con citas literales; absorbe detección de controversia",
                "weight": 0.40,
                "sources": ["exa", "llm_analysis"],
            },
            "mention_volume": {
                "description": "Cuánto se habla de la marca (absoluto + top dominios)",
                "weight": 0.25,
                "sources": ["exa"],
            },
            "sentiment_trend": {
                "description": "¿Mejora o empeora el sentiment con el tiempo? LLM sobre mitades históricas con fallback heurístico",
                "weight": 0.20,
                "sources": ["exa", "llm_analysis"],
            },
            "review_quality": {
                "description": "Presencia en plataformas de reviews profesionales y consumer",
                "weight": 0.15,
                "sources": ["exa"],
            },
        },
        "rules": [
            "si no hay mentions suficientes → score = 50 (neutral, no hay datos)",
        ],
    },

    "diferenciacion": {
        "description": "¿Dice algo distinto a sus competidores o es genérica?",
        "weight": 0.20,
        "features": {
            "positioning_clarity": {
                "description": "¿La marca articula una posición clara y defendible en su mercado?",
                "weight": 0.30,
                "sources": ["web_scrape", "llm_analysis"],
            },
            "uniqueness": {
                "description": "¿La marca usa lenguaje y vocabulario propios en vez de plantilla?",
                "weight": 0.25,
                "sources": ["web_scrape", "llm_analysis"],
            },
            "competitor_distance": {
                "description": "¿Se posiciona distinto a la competencia principal?",
                "weight": 0.20,
                "sources": ["exa", "llm_analysis"],
            },
            "content_authenticity": {
                "description": "¿El contenido se siente original y humano, no plantilla/AI sludge?",
                "weight": 0.15,
                "sources": ["content_analysis", "vision"],
            },
            "brand_personality": {
                "description": "¿La marca tiene voz y carácter propios?",
                "weight": 0.10,
                "sources": ["content_analysis", "exa"],
            },
        },
        "rules": [
            "si el lenguaje es >80% genérico → diferenciación cap a 25",
        ],
    },

    "vitalidad": {
        "description": "¿Está activa, publicando, evolucionando, o es una marca muerta?",
        "weight": 0.15,
        "features": {
            "content_recency": {
                "description": "¿Cuándo fue la última publicación detectable en fuentes terceras?",
                "weight": 0.40,
                "sources": ["exa"],
            },
            "publication_cadence": {
                "description": "Consistencia de la cadencia de publicación en los últimos 12 meses",
                "weight": 0.35,
                "sources": ["exa"],
            },
            "momentum": {
                "description": "¿Está construyendo o en mantenimiento? Juicio LLM con citas literales de menciones recientes",
                "weight": 0.25,
                "sources": ["exa", "llm_analysis"],
            },
        },
        "rules": [
            "si última publicación > 6 meses → vitalidad cap a 20",
            "si última publicación > 12 meses → vitalidad cap a 10",
        ],
    },
}

# Validate weights
assert abs(sum(d["weight"] for d in DIMENSIONS.values()) - 1.0) < 0.001, \
    "Dimension weights must sum to 1.0"

for name, dim in DIMENSIONS.items():
    feature_weights = sum(f["weight"] for f in dim["features"].values())
    assert abs(feature_weights - 1.0) < 0.001, \
        f"Feature weights in '{name}' must sum to 1.0, got {feature_weights}"
