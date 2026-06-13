"""SV9 rubric: components, ladders, pairs, and scoring rules as data.

This module is the SV9 counterpart of the legacy `src/dimensions.py`. It defines
the 9 scored components plus Coherencia, their cumulative ladders, the pair
groupings, the x2 multipliers, and the Magnetism cap rule.

Design source of truth: brand3-scanner-sv9-design-v1.md.

Rules encoded here:
- Ladder criteria are the INTERNAL evaluation rubric and the shared calibration
  rubric. They are NOT public copy: the founder-facing message is generated
  prose conditioned on the verdict (editorial layer, not this module).
- Every score and calibration record is traced against RUBRIC_VERSION. Any
  wording change to a ladder must bump the version.
- TILE SCORING (v2, product decision 2026-06-11): the evaluator judges every
  criterion independently (one boolean verdict per rung with a mandatory
  evidence quote) and the score is the COUNT OF TILES EARNED — not the
  consecutive run from the bottom. The strict ladder rule punished brands for
  criteria that describe alternative styles rather than prior achievements
  (46 non-monotonic profiles in the first corpus; e.g. a deliberately formal
  brand failing "intenta ser humana" was capped at 1/10 while demonstrably
  earning higher tiles). Not-evaluable tiles never score: coverage gaps are
  recorded, not punished or gifted. See src/sv9/aggregator.py.

Criteria wording status: draft (briefing v2.1 section 5). A joint writing
session will produce the final wording; tile format is closed, wording is not.
"""

from __future__ import annotations

RUBRIC_VERSION = "sv9-rubric-v2"

# Component statuses (doc section 3: detectado / no_detectado / no_evaluado).
STATUS_SCORED = "scored"            # detectado: evaluated against the ladder
STATUS_NOT_DETECTED = "not_detected"  # no_detectado: diagnosis, scores 0
STATUS_NOT_EVALUATED = "not_evaluated"  # no_evaluado: technical failure, scores 0, retryable

# Magnetism cap rule (doc section 3): if the normalized mean of the 8 base
# components is below this threshold (0-10 scale), Magnetism cannot exceed the cap.
MAGNETISM_CAP_BASE_THRESHOLD = 4.0
MAGNETISM_CAP_VALUE = 5

# Coherencia review queue rule (doc section 6): scans with Coherencia at or
# below this score enter the priority human review queue. Internal only.
COHERENCIA_REVIEW_THRESHOLD = 3

# Presentation order (doc section 12). Calculation order is independent.
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

COMPONENTS = {

    "mission": {
        "label": "Misión",
        "tldr_key": "mission",
        "scale": 5,
        "multiplier": 1,
        "pair": "mission_vision",
        "question": "¿Qué hace la marca concretamente hoy y para qué?",
        "level_zero": "No detectada en ninguna superficie pública.",
        "ladder": [
            {"rung": 1, "criterion": "Existe una misión detectable, aunque sea plantilla intercambiable: 'ser líderes', 'dar el mejor servicio'.", "internal_label": "plantilla"},
            {"rung": 2, "criterion": "La misión es concreta, aunque limitada al producto y no al problema.", "internal_label": "concreta-producto"},
            {"rung": 3, "criterion": "La misión es concreta y está anclada al problema real del usuario.", "internal_label": "anclada-problema"},
            {"rung": 4, "criterion": "La misión conecta con el resto del discurso y está publicada en la web principal, no escondida en el LinkedIn del fundador.", "internal_label": "publicada-conectada"},
            {"rung": 5, "criterion": "La misión redefine las reglas de su categoría y lo dice en público.", "internal_label": "redefine-categoria"},
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
        "ladder": [
            {"rung": 1, "criterion": "Existe una visión detectable, aunque sea humo aspiracional sin destino: 'transformar la industria'.", "internal_label": "humo-aspiracional"},
            {"rung": 2, "criterion": "El destino está nombrado, aunque sea indistinguible del de su competencia.", "internal_label": "destino-nombrado"},
            {"rung": 3, "criterion": "El destino es propio: imaginable o medible.", "internal_label": "destino-propio"},
            {"rung": 4, "criterion": "Se entiende el camino: la visión conecta con la misión.", "internal_label": "conecta-mision", "context_needs": ["mission"]},
            {"rung": 5, "criterion": "La visión define hacia dónde va el mercado, no solo la empresa.", "internal_label": "define-mercado"},
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
        "ladder": [
            {"rung": 1, "criterion": "Existen valores detectables, aunque sean higiénicos y vacíos: 'transparencia, innovación, calidad'.", "internal_label": "higienicos"},
            {"rung": 2, "criterion": "Los valores están declarados, aunque no se demuestren en el copy ni en la identidad.", "internal_label": "declarados"},
            {"rung": 3, "criterion": "Los valores son propios y con ángulo claro.", "internal_label": "propios"},
            {"rung": 4, "criterion": "Los valores son perceptibles en el tono sin necesidad de leer la lista de valores.", "internal_label": "perceptibles-tono"},
            {"rung": 5, "criterion": "Los valores son polarizantes: repelen activamente a quien no es su cliente ideal.", "internal_label": "polarizantes"},
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
        "ladder": [
            {"rung": 1, "criterion": "Existen atributos detectables, aunque sean adjetivos comodín aplicables a cualquier marca.", "internal_label": "comodin"},
            {"rung": 2, "criterion": "Los atributos están listados, aunque sin reflejo en producto o web.", "internal_label": "listados"},
            {"rung": 3, "criterion": "Los atributos son específicos y observables en la experiencia real.", "internal_label": "observables"},
            {"rung": 4, "criterion": "Los atributos son diferenciales frente al top 3 de su competencia.", "internal_label": "diferenciales"},
            {"rung": 5, "criterion": "Los atributos son inseparables de la marca: son su firma funcional.", "internal_label": "firma-funcional"},
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
        # Ladder order (briefing section 5): claridad, especificidad, diferencial, prueba.
        "ladder": [
            {"rung": 1, "criterion": "La oferta se deduce navegando, no leyendo.", "internal_label": "se-deduce"},
            {"rung": 2, "criterion": "La oferta es clara al menos para quien ya conoce la categoría.", "internal_label": "clara-iniciados"},
            {"rung": 3, "criterion": "La oferta es clara aunque commodity: la frase vale para cualquiera de su mercado.", "internal_label": "clara-commodity"},
            {"rung": 4, "criterion": "La propuesta está expresada en beneficios, no en features.", "internal_label": "beneficios"},
            {"rung": 5, "criterion": "La propuesta nombra a quién sirve: nicho definido.", "internal_label": "nicho"},
            {"rung": 6, "criterion": "La propuesta nombra el dolor crítico que resuelve.", "internal_label": "dolor-critico"},
            {"rung": 7, "criterion": "Hay diferencial explícito frente a las alternativas.", "internal_label": "diferencial"},
            {"rung": 8, "criterion": "El diferencial es difícil de copiar: hay mecanismo propio.", "internal_label": "mecanismo-propio"},
            {"rung": 9, "criterion": "Hay proof signals en la primera pantalla.", "internal_label": "proof-signals"},
            {"rung": 10, "criterion": "La promesa es verificable: datos reales, casos o garantías irrefutables.", "internal_label": "verificable"},
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
        "ladder": [
            {"rung": 1, "criterion": "Hay intención de tono, aunque sea inconsistente entre páginas.", "internal_label": "tono-inconsistente"},
            {"rung": 2, "criterion": "Intenta ser humana, aunque caiga en clichés.", "internal_label": "humana-cliches"},
            {"rung": 3, "criterion": "Es correcta y profesional, sin arquetipo.", "internal_label": "correcta"},
            {"rung": 4, "criterion": "Hay arquetipo insinuado, aunque no sostenido.", "internal_label": "arquetipo-insinuado"},
            {"rung": 5, "criterion": "El arquetipo es claro en los titulares.", "internal_label": "arquetipo-titulares"},
            {"rung": 6, "criterion": "Es consistente de titulares a microcopy.", "internal_label": "consistente-microcopy"},
            {"rung": 7, "criterion": "Es consistente también en redes y producto.", "internal_label": "consistente-redes"},
            {"rung": 8, "criterion": "Tiene rasgos propios reconocibles: giros, ritmo, humor.", "internal_label": "rasgos-propios"},
            {"rung": 9, "criterion": "Pasa el test del logo tapado: sabes quién habla sin ver la marca.", "internal_label": "logo-tapado"},
            {"rung": 10, "criterion": "La personalidad genera contenido citable; otros la imitan.", "internal_label": "citable"},
        ],
    },

    "brand_idea": {
        "label": "Idea de marca",
        "tldr_key": "brand_idea",
        "scale": 10,
        "multiplier": 1,
        "pair": None,
        # The low rungs (logo/color, estética, sistema) are judgeable from
        # visual evidence alone even when no conceptual brand idea was detected
        # in text; only the concept rungs (5+) need the detection. Without this,
        # a missing concept erases observable visual identity.
        "evaluate_on_signals": True,
        "question": "¿Qué idea conceptual conecta categoría, oferta, expresión y metáfora?",
        "level_zero": "Plantilla sin alterar: identidad visual nula.",
        "ladder": [
            {"rung": 1, "criterion": "Hay logo y color, aunque sin sistema detrás.", "internal_label": "logo-color"},
            {"rung": 2, "criterion": "Hay estética, aunque sea la genérica de su categoría.", "internal_label": "estetica-generica"},
            {"rung": 3, "criterion": "Hay sistema visual básico y consistente.", "internal_label": "sistema-basico"},
            {"rung": 4, "criterion": "Es correcta visualmente, aunque vacía conceptualmente.", "internal_label": "correcta-vacia"},
            {"rung": 5, "criterion": "Hay concepto declarado, aunque no ejecutado.", "internal_label": "concepto-declarado"},
            {"rung": 6, "criterion": "El concepto está ejecutado en la web principal.", "internal_label": "concepto-ejecutado"},
            {"rung": 7, "criterion": "El visual traduce propósito y personalidad: dirección de arte intencionada.", "internal_label": "direccion-arte"},
            {"rung": 8, "criterion": "El sistema es consistente en todas las superficies.", "internal_label": "consistente-superficies"},
            {"rung": 9, "criterion": "Hay universo estético propio reconocible.", "internal_label": "universo-propio"},
            {"rung": 10, "criterion": "La firma visual eleva el precio percibido: el envoltorio hace al producto parecer mejor de lo que sus features justifican.", "internal_label": "firma-visual"},
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
        "ladder": [
            {"rung": 1, "criterion": "El porqué se intuye por contexto, aunque no haya nada escrito.", "internal_label": "intuido"},
            {"rung": 2, "criterion": "El 'about' cuenta al menos qué hacen, aunque no por qué existen.", "internal_label": "about-que"},
            {"rung": 3, "criterion": "Hay propósito declarado, aunque genérico: 'hacer el mundo mejor'.", "internal_label": "declarado-generico"},
            {"rung": 4, "criterion": "El propósito, aunque genérico, está anclado a su categoría.", "internal_label": "anclado-categoria"},
            {"rung": 5, "criterion": "El propósito es explícito y propio, aunque aislado del producto.", "internal_label": "explicito-propio"},
            {"rung": 6, "criterion": "El propósito conecta con la propuesta de valor.", "internal_label": "conecta-propuesta", "context_needs": ["value_proposition"]},
            {"rung": 7, "criterion": "El propósito conecta con misión y visión: la cadena del porqué se sostiene.", "internal_label": "cadena-porque", "context_needs": ["mission", "vision"]},
            {"rung": 8, "criterion": "El tono y el diseño lo respiran sin leer el 'about'.", "internal_label": "respirado"},
            {"rung": 9, "criterion": "Está demostrado en una decisión de negocio pública: pricing, renuncias, open source.", "internal_label": "decision-publica"},
            {"rung": 10, "criterion": "Está demostrado en varias decisiones verificables por terceros: el porqué es su reputación.", "internal_label": "reputacion"},
        ],
    },

    "magnetism": {
        "label": "Magnetism",
        "tldr_key": "magnetism",
        "scale": 10,
        "multiplier": 2,
        "pair": None,
        "question": "¿Qué frase, tensión o promesa es más probable que se recuerde — y está ganada, no solo expresada?",
        "level_zero": "Invisible: nada retiene la atención.",
        "ladder": [
            {"rung": 1, "criterion": "Consigue atención de cortesía: se lee, aunque se olvide al instante.", "internal_label": "cortesia"},
            {"rung": 2, "criterion": "Es legible aunque forgettable: sin tensión narrativa ni gancho.", "internal_label": "forgettable"},
            {"rung": 3, "criterion": "Es funcional: se entiende, aunque no se desee.", "internal_label": "funcional"},
            {"rung": 4, "criterion": "Hay un gancho detectable, aunque blando.", "internal_label": "gancho-blando"},
            {"rung": 5, "criterion": "Hay hook claro que toca el dolor del cliente.", "internal_label": "hook-dolor"},
            {"rung": 6, "criterion": "Genera interés genuino: invita a seguir explorando.", "internal_label": "interes"},
            {"rung": 7, "criterion": "Genera deseo: el packaging hace al producto parecer superior.", "internal_label": "deseo"},
            {"rung": 8, "criterion": "Genera preferencia activa frente a competencia con más features.", "internal_label": "preferencia"},
            {"rung": 9, "criterion": "Genera orgullo de pertenencia: los usuarios presumen de usarla.", "internal_label": "orgullo"},
            {"rung": 10, "criterion": "Es culto: irracionalmente atractiva, la marca tira sola.", "internal_label": "culto"},
        ],
    },

    "coherencia": {
        "label": "Coherencia",
        "tldr_key": None,  # No detection of its own: reads the whole (doc section 6).
        "scale": 10,
        "multiplier": 2,
        "pair": None,
        "question": "¿Los componentes cuentan la misma historia entre sí y en todos los espacios digitales?",
        "level_zero": "Contradicciones graves: prometen simplicidad y el producto es complejo.",
        # Axis tags are draft metadata for the writing session (doc section 17):
        # internal = sintonía entre los 9 componentes; external = web vs resto
        # de espacios digitales.
        "ladder": [
            {"rung": 1, "criterion": "Las contradicciones son solo parciales, en mensajes clave.", "internal_label": "contradicciones-parciales", "axis": "both"},
            {"rung": 2, "criterion": "No hay contradicción, aunque las piezas vivan en compartimentos estancos.", "internal_label": "estancos", "axis": "internal"},
            {"rung": 3, "criterion": "Hay conexiones entre componentes, aunque débiles.", "internal_label": "conexiones-debiles", "axis": "internal"},
            {"rung": 4, "criterion": "Lo que dicen, lo hacen: sin fricciones graves entre discurso y comportamiento.", "internal_label": "dicen-hacen", "axis": "external"},
            {"rung": 5, "criterion": "Propósito, misión y propuesta están alineados en el texto.", "internal_label": "alineacion-texto", "axis": "internal"},
            {"rung": 6, "criterion": "El tono coincide con los valores declarados.", "internal_label": "tono-valores", "axis": "internal"},
            {"rung": 7, "criterion": "El diseño cuenta la misma historia que el copy.", "internal_label": "diseno-copy", "axis": "internal"},
            {"rung": 8, "criterion": "La alineación es profunda en todas las superficies públicas: la web y el resto de espacios digitales dicen lo mismo.", "internal_label": "superficies", "axis": "external"},
            {"rung": 9, "criterion": "Cada punto de contacto retroalimenta el propósito central.", "internal_label": "retroalimenta", "axis": "both"},
            {"rung": 10, "criterion": "Inseparable: imposible distinguir dónde acaba el producto y empieza la marca.", "internal_label": "inseparable", "axis": "both"},
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


# --- Integrity checks (same spirit as legacy dimensions.py) ---

assert set(PRESENTATION_ORDER) == set(COMPONENTS), "Presentation order must cover every component exactly once"
assert len(PRESENTATION_ORDER) == 10, "SV9 is 9 scored components plus Coherencia"
assert set(BASE_COMPONENTS) == set(COMPONENTS) - {"magnetism", "coherencia"}, \
    "Base components are everything except Magnetism and Coherencia"

_total = sum(component_max_points(key) for key in COMPONENTS)
assert _total == 100, f"Brand3 Score must total 100, got {_total}"

for _key, _spec in COMPONENTS.items():
    assert len(_spec["ladder"]) == _spec["scale"], \
        f"Ladder for '{_key}' must have exactly {_spec['scale']} rungs, got {len(_spec['ladder'])}"
    for _idx, _rung in enumerate(_spec["ladder"], start=1):
        assert _rung["rung"] == _idx, f"Ladder for '{_key}' must be consecutive from 1; rung {_idx} is {_rung['rung']}"
        assert _rung["criterion"].strip(), f"Ladder for '{_key}' rung {_idx} has an empty criterion"
    for _ctx_key in {c for r in _spec["ladder"] for c in r.get("context_needs", [])}:
        assert _ctx_key in COMPONENTS, f"Ladder for '{_key}' references unknown component '{_ctx_key}'"

_pairs: dict[str, list[str]] = {}
for _key, _spec in COMPONENTS.items():
    if _spec["pair"]:
        _pairs.setdefault(_spec["pair"], []).append(_key)
for _pair_name, _members in _pairs.items():
    assert len(_members) == 2, f"Pair '{_pair_name}' must have exactly 2 members, got {_members}"
    assert all(COMPONENTS[m]["scale"] == 5 for m in _members), f"Pair '{_pair_name}' members must be 0-5 scale"
