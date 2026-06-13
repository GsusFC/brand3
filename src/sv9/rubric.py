"""SV9 rubric (baldosas v3.1): components, tiles, pairs, and scoring rules as data.

This module is the SV9 counterpart of the legacy `src/dimensions.py`. It defines
the 9 scored components plus Coherencia, their 80 independent tiles (baldosas),
the pair groupings, the x2 multipliers, the Magnetism cap rule, and the
confidence thresholds.

Design source of truth: docs/baldosas-v3.1.md.

Rules encoded here:
- TILE MODEL (v3.1, replaces the cumulative ladders of v2). Each tile is an
  independent key characteristic that is met or not. A component's score is the
  number of lit tiles — there is no order and no dependency between tiles. The
  tile texts in `condition` are FINAL COPY (briefing section 3), shown verbatim
  in the canvas and the calibration form.
- THREE STATES, TWO MEANINGS OF ZERO. A tile is `ok` (lit, +1 point), `no`
  (off: the snapshot proves the brand does not communicate or meet it — a brand
  failure) or `sin_evidencia` (blind spot: the snapshot structurally cannot hold
  the proof — not a brand failure). `no` and `sin_evidencia` both score 0 but are
  never conflated in the report or the UI.
- CONFIDENCE. A component drops to `media` confidence with 2 `sin_evidencia`
  tiles and to `baja` with 3 or more.
- Every score and calibration record is traced against RUBRIC_VERSION. Any
  wording change to a tile must bump the version (governance: tiles change by
  calibration, not by intuition; see docs/baldosas-v3.1.md section 5).
- The LLM judges tiles and quotes evidence. The score, the x2 multipliers, the
  confidence index, and the Magnetism cap are all computed by code
  (src/sv9/aggregator.py), never by the model.
"""

from __future__ import annotations

RUBRIC_VERSION = "baldosas-v3.1"

# The model label persisted on every scan and shown in the ranking during the
# migration window. Scans from earlier rubric versions are labelled "v2".
MODEL_LABEL = "v3.1"
LEGACY_MODEL_LABEL = "v2"

# Component statuses (same lifecycle as v2).
STATUS_SCORED = "scored"            # detectado: evaluated against the tiles
STATUS_NOT_DETECTED = "not_detected"  # no_detectado: diagnosis, scores 0
STATUS_NOT_EVALUATED = "not_evaluated"  # no_evaluado: technical failure, scores 0, retryable

# Tile states (briefing section 1, rule 3).
ESTADO_OK = "ok"
ESTADO_NO = "no"
ESTADO_SIN_EVIDENCIA = "sin_evidencia"
TILE_ESTADOS = (ESTADO_OK, ESTADO_NO, ESTADO_SIN_EVIDENCIA)

# Confidence thresholds (briefing section 1, rule 4; section 4).
CONFIDENCE_ALTA = "alta"
CONFIDENCE_MEDIA = "media"
CONFIDENCE_BAJA = "baja"
CONFIDENCE_MEDIA_BLIND_SPOTS = 2
CONFIDENCE_BAJA_BLIND_SPOTS = 3

# Magnetism cap rule (briefing section 1, rule 5): if the normalized mean of the
# 8 base components is below this threshold (0-10 scale), the lit Magnetism tiles
# are capped at MAGNETISM_CAP_VALUE (10/20 after the x2).
MAGNETISM_CAP_BASE_THRESHOLD = 4.0
MAGNETISM_CAP_VALUE = 5

# Coherencia review queue rule: scans with Coherencia at or below this score
# enter the priority human review queue. Internal only.
COHERENCIA_REVIEW_THRESHOLD = 3

# Presentation order. Calculation order is independent.
PRESENTATION_ORDER = [
    "mission",
    "vision",
    "values",
    "attributes",
    "value_proposition",
    "personality",
    "brand_idea",
    "core_purpose",
    "magnetism",
    "coherencia",
]

# The 8 base components used for the Magnetism cap mean (everything except
# magnetism and coherencia).
BASE_COMPONENTS = [
    "mission",
    "vision",
    "values",
    "attributes",
    "value_proposition",
    "personality",
    "brand_idea",
    "core_purpose",
]

# C8's evaluator note lives inside the tile definition (prompt técnico, step 1).
_C8_NOTE = (
    "El scanner no puede probar el producto. Por defecto sin_evidencia, salvo que "
    "el snapshot contenga pruebas sociales contundentes: reviews, casos de estudio "
    "detallados o demos comprobables."
)

COMPONENTS = {

    "mission": {
        "label": "Misión",
        "tldr_key": "mission",
        "scale": 5,
        "multiplier": 1,
        "pair": "mission_vision",
        "question": "¿Qué hace la marca concretamente hoy y para qué?",
        "level_zero": "No detectada en ninguna superficie pública.",
        "tiles": [
            {"id": "M1", "name": "Detectada", "condition": "Hay una misión identificable en superficie pública propia."},
            {"id": "M2", "name": "Propia", "condition": "No es intercambiable con cualquier marca de su categoría (“ser líderes” no enciende)."},
            {"id": "M3", "name": "Anclada", "condition": "Conecta con un problema real: del usuario, de la categoría, del mundo o una frontera tecnológica."},
            {"id": "M4", "name": "Coherente", "condition": "No contradice propósito ni propuesta; encaja en el discurso."},
            {"id": "M5", "name": "Ambiciosa", "condition": "Marca un camino que lidera o redefine su categoría."},
        ],
    },

    "vision": {
        "label": "Visión",
        "tldr_key": "vision",
        "scale": 5,
        "multiplier": 1,
        "pair": "mission_vision",
        "question": "¿Qué futuro o cambio de categoría intenta construir la marca?",
        "level_zero": "No detectada.",
        "tiles": [
            {"id": "V1", "name": "Detectada", "condition": "Hay un destino identificable."},
            {"id": "V2", "name": "Concreta", "condition": "El destino se nombra; “transformar la industria” no enciende."},
            {"id": "V3", "name": "Propia", "condition": "Distinguible de la visión de su competencia."},
            {"id": "V4", "name": "Conectada", "condition": "Se entiende el camino entre la misión de hoy y el destino.", "context_needs": ["mission"]},
            {"id": "V5", "name": "De categoría", "condition": "Define hacia dónde va el mercado, no solo la empresa."},
        ],
    },

    "values": {
        "label": "Valores",
        "tldr_key": "values",
        "scale": 5,
        "multiplier": 1,
        "pair": "values_attributes",
        "question": "¿Qué valores defiende la marca a través de lo que dice o hace?",
        "level_zero": "No detectados.",
        "tiles": [
            {"id": "VA1", "name": "Detectados", "condition": "Declarados o inferibles en tono y decisiones del snapshot."},
            {"id": "VA2", "name": "Propios", "condition": "Con ángulo; “transparencia, innovación, calidad” no enciende."},
            {"id": "VA3", "name": "Perceptibles", "condition": "El tono los transmite sin leer ninguna lista."},
            {"id": "VA4", "name": "Demostrados", "condition": "Copy, producto o decisiones públicas del snapshot los ejecutan."},
            {"id": "VA5", "name": "Polarizantes", "condition": "Repelen activamente a quien no es su cliente o talento ideal."},
        ],
    },

    "attributes": {
        "label": "Atributos",
        "tldr_key": "attributes",
        "scale": 5,
        "multiplier": 1,
        "pair": "values_attributes",
        "question": "¿Qué atributos demuestra la marca de forma consistente?",
        "level_zero": "No detectados.",
        "tiles": [
            {"id": "A1", "name": "Detectados", "condition": "Características tangibles identificables."},
            {"id": "A2", "name": "Específicos", "condition": "Sin adjetivos comodín."},
            {"id": "A3", "name": "Verificables", "condition": "Comprobables en producto o experiencia según el snapshot."},
            {"id": "A4", "name": "Diferenciales", "condition": "Distintos frente a alternativas. Requiere evidencia de cohorte en el snapshot; si no la hay, sin_evidencia.", "blind_spot": True},
            {"id": "A5", "name": "Integrados", "condition": "La marca los usa como argumento de venta, no solo los lista."},
        ],
    },

    "value_proposition": {
        "label": "Propuesta de valor",
        "tldr_key": "value_proposition",
        "scale": 10,
        "multiplier": 1,
        "pair": None,
        "question": "¿Qué ofrece la marca, a quién, y qué cambia para esa audiencia?",
        "level_zero": "Ausente: la hero no dice qué venden.",
        "tiles": [
            {"id": "P1", "name": "Detectada", "condition": "La hero dice qué venden."},
            {"id": "P2", "name": "Clara", "condition": "Se entiende sin conocer la categoría."},
            {"id": "P3", "name": "En beneficios", "condition": "Habla de resultado, no solo de features."},
            {"id": "P4", "name": "Público inequívoco", "condition": "Nombrado, o evidente por producto y contexto."},
            {"id": "P5", "name": "Tensión nombrada", "condition": "Se sabe qué dolor, deseo, necesidad o frontera tecnológica resuelve o rompe."},
            {"id": "P6", "name": "Propia", "condition": "La frase no vale para su competencia."},
            {"id": "P7", "name": "Diferencial explícito", "condition": "Dice por qué ella y no las alternativas. Requiere cohorte; si no, sin_evidencia.", "blind_spot": True},
            {"id": "P8", "name": "Mecanismo propio", "condition": "El cómo es identificable y difícil de copiar."},
            {"id": "P9", "name": "Prueba a la vista", "condition": "Proof signals en la primera pantalla."},
            {"id": "P10", "name": "Promesa verificable", "condition": "Datos, casos o garantías irrefutables en el snapshot."},
        ],
    },

    "personality": {
        "label": "Personalidad / Arquetipo",
        "tldr_key": "personality",
        "scale": 10,
        "multiplier": 1,
        "pair": None,
        "question": "¿Qué personalidad ejecuta la marca a través de tono, vocabulario, comportamiento y postura visual?",
        "level_zero": "Robótica: plantilla B2B estándar.",
        "tiles": [
            {"id": "PE1", "name": "Voz detectable", "condition": "Hay un tono, no una plantilla."},
            {"id": "PE2", "name": "Sin clichés", "condition": "No cae en los tics de su categoría."},
            {"id": "PE3", "name": "Arquetipo identificable", "condition": "Se puede nombrar: rebelde, sabio, creador, maverick…"},
            {"id": "PE4", "name": "Consistente entre páginas", "condition": "El tono no cambia de la home al pricing."},
            {"id": "PE5", "name": "Consistente en microcopy", "condition": "Botones, errores y detalles hablan igual."},
            {"id": "PE6", "name": "Consistente en redes y producto", "condition": "La voz sobrevive fuera de la web."},
            {"id": "PE7", "name": "Rasgos propios", "condition": "Giros, ritmo, humor o dureza reconocibles."},
            {"id": "PE8", "name": "Coherente con valores e idea", "condition": "La personalidad ejecuta lo que la marca dice ser. Temperatura libre."},
            {"id": "PE9", "name": "Test del logo tapado", "condition": "Se reconoce quién habla sin ver la marca."},
            {"id": "PE10", "name": "Citable", "condition": "Genera contenido que otros recuerdan o imitan."},
        ],
    },

    "brand_idea": {
        "label": "Idea de marca",
        "tldr_key": "brand_idea",
        "scale": 10,
        "multiplier": 1,
        "pair": None,
        # The visual tiles (I1-I3, I6-I9) are judgeable from visual evidence
        # alone even when no conceptual brand idea was detected in text, so the
        # component evaluates on signals when detection is empty.
        "evaluate_on_signals": True,
        "question": "¿Qué idea conceptual conecta categoría, oferta, expresión y metáfora?",
        "level_zero": "Plantilla sin alterar: identidad visual nula.",
        "tiles": [
            {"id": "I1", "name": "Identidad existente", "condition": "No es una plantilla sin alterar."},
            {"id": "I2", "name": "Sistema", "condition": "Logo, color y tipografía funcionan como conjunto."},
            {"id": "I3", "name": "No genérica", "condition": "Se distingue de la estética estándar de su categoría."},
            {"id": "I4", "name": "Concepto detectable", "condition": "Hay una idea detrás, declarada o evidente."},
            {"id": "I5", "name": "Concepto ejecutado", "condition": "La idea se ve en la web principal, no solo se declara."},
            {"id": "I6", "name": "Dirección de arte", "condition": "Decisiones visuales intencionadas, no decorativas."},
            {"id": "I7", "name": "Traduce la estrategia", "condition": "El visual expresa propósito y personalidad."},
            {"id": "I8", "name": "Consistente", "condition": "El sistema se sostiene en todas las superficies del snapshot."},
            {"id": "I9", "name": "Universo propio", "condition": "Estética reconocible como suya."},
            {"id": "I10", "name": "Eleva el precio percibido", "condition": "El envoltorio hace al producto parecer mejor de lo que sus features justifican."},
        ],
    },

    "core_purpose": {
        "label": "Propósito",
        "tldr_key": "core_purpose",
        "scale": 10,
        "multiplier": 1,
        "pair": None,
        "question": "¿Por qué existe la marca más allá del producto?",
        "level_zero": "Ningún rastro del porqué en ninguna superficie pública.",
        "tiles": [
            {"id": "PR1", "name": "Detectado", "condition": "Hay un porqué en alguna superficie."},
            {"id": "PR2", "name": "Explícito", "condition": "Escrito, no solo intuible."},
            {"id": "PR3", "name": "Más allá del qué", "condition": "Responde por qué existen, no qué hacen."},
            {"id": "PR4", "name": "Propio", "condition": "“Hacer el mundo mejor” no enciende."},
            {"id": "PR5", "name": "Anclado", "condition": "Conecta con su categoría y su producto."},
            {"id": "PR6", "name": "Conectado a la propuesta", "condition": "El porqué justifica el qué venden.", "context_needs": ["value_proposition"]},
            {"id": "PR7", "name": "Cadena completa", "condition": "Propósito, misión y visión se sostienen juntos.", "context_needs": ["mission", "vision"]},
            {"id": "PR8", "name": "Respirado", "condition": "Tono y diseño lo transmiten sin leer el “about”."},
            {"id": "PR9", "name": "Demostrado", "condition": "Al menos una decisión de negocio pública del snapshot lo ejecuta."},
            {"id": "PR10", "name": "Reputación", "condition": "Varias decisiones verificables por terceros; el porqué es su prueba social."},
        ],
    },

    "magnetism": {
        "label": "Magnetism",
        "tldr_key": "magnetism",
        "scale": 10,
        "multiplier": 2,
        "pair": None,
        "question": "¿Qué frase, tensión o promesa retiene, y por qué mecanismo: dolor, deseo, asombro, pertenencia o estatus?",
        "level_zero": "Invisible: nada retiene la atención.",
        "tiles": [
            {"id": "MG1", "name": "Retiene", "condition": "Algo detiene el scroll, verbal o visual."},
            {"id": "MG2", "name": "Mecanismo identificable", "condition": "Se sabe cuál opera: dolor, deseo, asombro, pertenencia o estatus."},
            {"id": "MG3", "name": "Hook", "condition": "Gancho claro anclado a una tensión real de su audiencia."},
            {"id": "MG4", "name": "Tensión narrativa", "condition": "Hay historia, no solo descripción."},
            {"id": "MG5", "name": "Memorable", "condition": "Una frase o imagen que se queda."},
            {"id": "MG6", "name": "Invita a explorar", "condition": "La huella pide seguir navegando."},
            {"id": "MG7", "name": "Genera deseo", "condition": "El packaging hace al producto parecer superior."},
            {"id": "MG8", "name": "Genera preferencia", "condition": "Da razones para elegirla frente a alternativas con más features."},
            {"id": "MG9", "name": "Pertenencia o estatus", "condition": "Señales de orgullo: comunidad que presume o posición que se exhibe.", "blind_spot": True},
            {"id": "MG10", "name": "Gravedad propia", "condition": "Atrae talento, prensa o comunidad sin empujar, según evidencia del snapshot.", "blind_spot": True},
        ],
    },

    "coherencia": {
        "label": "Coherencia",
        "tldr_key": None,  # No detection of its own: reads the whole.
        "scale": 10,
        "multiplier": 2,
        "pair": None,
        "question": "¿Los componentes cuentan la misma historia entre sí y en todos los espacios digitales?",
        "level_zero": "Contradicciones graves: prometen simplicidad y el producto es complejo.",
        "tiles": [
            {"id": "C1", "name": "Sin contradicciones graves", "condition": "No prometen simplicidad con un producto laberíntico."},
            {"id": "C2", "name": "Sin contradicciones parciales", "condition": "Los mensajes clave no se pisan entre sí."},
            {"id": "C3", "name": "Propósito-misión", "condition": "El porqué y el camino encajan."},
            {"id": "C4", "name": "Misión-propuesta", "condition": "Lo que persiguen y lo que venden encajan."},
            {"id": "C5", "name": "Valores en el tono", "condition": "La personalidad ejecuta los valores declarados o inferidos."},
            {"id": "C6", "name": "Diseño-copy", "condition": "El visual cuenta la misma historia que el texto."},
            {"id": "C7", "name": "Web-redes", "condition": "El discurso sobrevive al cambio de canal."},
            {"id": "C8", "name": "Marca-producto", "condition": "La experiencia real cumple lo que la marca proyecta.", "note": _C8_NOTE, "blind_spot": True},
            {"id": "C9", "name": "Refuerzo mutuo", "condition": "Las piezas se apoyan entre sí, no solo conviven."},
            {"id": "C10", "name": "Inseparable", "condition": "Imposible distinguir dónde acaba el producto y empieza la marca."},
        ],
    },
}


def component_max_points(key: str) -> int:
    """Points this component contributes to the Brand3 Score at its ceiling."""
    spec = COMPONENTS[key]
    return spec["scale"] * spec["multiplier"]


def component_points(key: str, score: int) -> int:
    """Points contributed by a component given its 0-scale score."""
    spec = COMPONENTS[key]
    return score * spec["multiplier"]


def tile_ids(key: str) -> list[str]:
    """The tile IDs for a component, in presentation order."""
    return [tile["id"] for tile in COMPONENTS[key]["tiles"]]


def tile_index() -> dict[str, dict[str, str]]:
    """Flat {tile_id: {component, name, condition}} for validation and reports."""
    index: dict[str, dict[str, str]] = {}
    for key, spec in COMPONENTS.items():
        for tile in spec["tiles"]:
            index[tile["id"]] = {
                "component": key,
                "name": tile["name"],
                "condition": tile["condition"],
            }
    return index


def confidence_from_blind_spots(blind_spot_count: int) -> str:
    """Component confidence from its count of `sin_evidencia` tiles."""
    if blind_spot_count >= CONFIDENCE_BAJA_BLIND_SPOTS:
        return CONFIDENCE_BAJA
    if blind_spot_count >= CONFIDENCE_MEDIA_BLIND_SPOTS:
        return CONFIDENCE_MEDIA
    return CONFIDENCE_ALTA


# --- Integrity checks (same spirit as legacy dimensions.py) ---

assert set(PRESENTATION_ORDER) == set(COMPONENTS), "Presentation order must cover every component exactly once"
assert len(PRESENTATION_ORDER) == 10, "SV9 is 9 scored components plus Coherencia"
assert set(BASE_COMPONENTS) == set(COMPONENTS) - {"magnetism", "coherencia"}, \
    "Base components are everything except Magnetism and Coherencia"

_total = sum(component_max_points(key) for key in COMPONENTS)
assert _total == 100, f"Brand3 Score must total 100, got {_total}"

_all_tiles = 0
_seen_ids: set[str] = set()
for _key, _spec in COMPONENTS.items():
    assert len(_spec["tiles"]) == _spec["scale"], \
        f"Component '{_key}' must have exactly {_spec['scale']} tiles, got {len(_spec['tiles'])}"
    for _tile in _spec["tiles"]:
        assert _tile["id"] not in _seen_ids, f"Duplicate tile id {_tile['id']}"
        _seen_ids.add(_tile["id"])
        assert _tile["condition"].strip(), f"Tile {_tile['id']} has an empty condition"
        assert _tile["name"].strip(), f"Tile {_tile['id']} has an empty name"
        _all_tiles += 1
    for _ctx_key in {c for t in _spec["tiles"] for c in t.get("context_needs", [])}:
        assert _ctx_key in COMPONENTS, f"Component '{_key}' references unknown component '{_ctx_key}'"

assert _all_tiles == 80, f"The baldosas model has exactly 80 tiles, got {_all_tiles}"

_pairs: dict[str, list[str]] = {}
for _key, _spec in COMPONENTS.items():
    if _spec["pair"]:
        _pairs.setdefault(_spec["pair"], []).append(_key)
for _pair_name, _members in _pairs.items():
    assert len(_members) == 2, f"Pair '{_pair_name}' must have exactly 2 members, got {_members}"
    assert all(COMPONENTS[m]["scale"] == 5 for m in _members), f"Pair '{_pair_name}' members must be 0-5 scale"
