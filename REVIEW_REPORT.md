# Review report — Dimensión Diferenciación

## Resumen ejecutivo

- **Decisión**: APPROVE
- **Fixes aplicados**: 1
- **Bloqueantes**: 0
- **Advertencias**: 2

## Fixes aplicados por el revisor

### 1. `91c74be` — Validación de shape en las listas del output LLM de `uniqueness`

**Archivo:** `src/features/diferenciacion.py:268-295`.

`_uniqueness` validaba `verdict` y `uniqueness_score`, pero las cuatro listas que el LLM devuelve (`unique_phrases`, `generic_phrases`, `brand_vocabulary`, `competitor_overlap_signals`) se pasaban sin filtrar:

```python
"unique_phrases": result.get("unique_phrases") or [],
```

Si el LLM hubiera devuelto un string en vez de lista, o items no-string, quedaban en `raw_value` con shape inconsistente. Regla #9 del review brief — trivial.

**Fix:** helper `_clean_string_list(items, limit=20)` que descarta no-strings, strips whitespace y clamps a 20. Si las cuatro listas quedan vacías y `verdict != "unclear"`, degrada `confidence` a 0.5 y añade `raw_value.reason = "llm_partial_evidence"` — mismo patrón ya establecido en `coherencia` y `vitalidad`.

## Bloqueantes restantes

Ninguno.

## Advertencias

### A1. Learning system sigue referenciando la feature eliminada `generic_language_score`

**Archivos:** `src/learning/calibration.py:135,143,193`, `src/learning/applier.py:40`, y `tests/test_learning.py` (múltiples líneas).

`calibration.py` analiza rows históricos buscando `feature_name == "generic_language_score"` para generar candidates de la rule `lenguaje_generico`. Esa feature ya no existe — el engine ahora chequea `uniqueness`. El código no crashea (solo nunca encuentra rows nuevos), pero el loop de aprendizaje sobre generic language quedó dormido.

El prompt de review no lo incluye en scope — learning system queda fuera del refactor de Diferenciación. Recomendación para humano: migrar esas referencias a `uniqueness` (con la semántica invertida: low uniqueness = generic) cuando se retome el learning system. No bloquea merge.

### A2. Rule `lenguaje_generico` mantiene su nombre (opción B del prompt)

Codex eligió la opción B: mantener `condition="lenguaje_generico"` y cambiar el check para leer `uniqueness` (`engine.py:60, 126-128`). Coherente en:
- `src/scoring/engine.py`
- `src/niche/profiles.py:35, 56, 77` — overrides por perfil siguen usando la key `lenguaje_generico`.
- `src/dimensions.py` — string human-readable en la lista `rules` no referencia nombres técnicos.

No hay inconsistencia parcial. Es una decisión de diseño aceptable, pero quien lea el código por primera vez puede extrañarse de que la rule se llame `lenguaje_generico` y lea la feature `uniqueness`. Un comentario en `engine.py:126` ayudaría. No bloqueante.

## Tests

```
132 passed in 1.46s
```

Suite completa verde tras el fix. Tests focales de Diferenciación + scoring engine corridos una vez antes y una vez después del fix (ambas rondas 16/16 y suite 132/132).

### Cumplimiento del prompt verificado

- ✅ 5 features con nombres exactos: `positioning_clarity`, `uniqueness`, `competitor_distance`, `content_authenticity`, `brand_personality` (`dimensions.py:113-138`, `diferenciacion.py:97-101`).
- ✅ Pesos `0.30 / 0.25 / 0.20 / 0.15 / 0.10`. Suman 1.0 (assert en `dimensions.py` pasa en import).
- ✅ `raw_value` de las 5 features es dict nativo.
- ✅ `diferenciacion_llm.py` eliminado (no aparece en árbol).
- ✅ Features viejas (`unique_value_prop`, `generic_language_score`, `brand_vocabulary` como top-level) eliminadas del extractor y de `dimensions.py`. `brand_vocabulary` sigue como **sub-key** del `raw_value` de `uniqueness`, no como feature independiente — correcto.
- ✅ `DiferenciacionExtractor.__init__` acepta `llm` (verificado en tests y en `brand_service.py`).
- ✅ `LLMAnalyzer` gana `analyze_positioning_clarity` y `analyze_uniqueness`; `analyze_positioning` y `analyze_differentiation` conservados.
- ✅ Regla `lenguaje_generico` coherente cross-file (opción B).
- ✅ Validación shape en `_positioning_clarity` (verdict enum, score numérico, `evidence` filtrada vía `_clean_positioning_evidence`, degradación a `llm_partial_evidence`).
- ✅ Validación shape en `_uniqueness` tras el fix.
- ✅ Fallback de `uniqueness` normaliza por longitud: `ratio = len(generic_hits) / sentence_count` (`diferenciacion.py:236`). Era el bug documentado en `scoring_review.md`. OK.
- ✅ `AuthenticityAnalyzer` intacto (no tocado por el refactor).

### Bugs potenciales revisados, descartados

- División por cero: `_uniqueness_fallback` ya guardiaba `sentence_count` (`if sentence_count else 0.0`).
- `CompetitorData=None`: ambos métodos LLM hacen `if competitor_data:` antes de iterar.
- `max([])` / slicing: no encontrado en los caminos nuevos.

## Notas cualitativas

- Evidencia literal preservada: `positioning_clarity.raw_value.evidence` con `{quote, signal}`; `uniqueness.raw_value` con 4 listas de strings + `reasoning`. Excelente material para conversación comercial ("aquí están las frases de plantilla que detectamos en vuestra web").
- Normalización por longitud en el fallback de `uniqueness` es la decisión correcta — el bug original del scoring generaba falsos "muy genérico" para webs largas con volumen alto de copy incluso cuando el ratio era bajo.
- `_competitor_distance` usa `CompetitorData.comparisons` con distancias ya calculadas; `raw_value` con `closest_competitor`, `most_different`, y `brand_unique_terms`. Útil.
- Patrón de diseño uniforme con Vitalidad, Presencia y Coherencia: LLM-first con fallback heurístico + dict raw_value estructurado + validación de enum y listas.

---

**Branch:** `main`
**Último commit del refactor:** `bb95068` (Codex) + `91c74be` (fix review)
**Base:** `main`

---

# Review report — Dimensión Presencia

## Resumen ejecutivo

- **Decisión**: APPROVE
- **Fixes aplicados**: 1
- **Bloqueantes**: 0
- **Advertencias**: 2

## Fixes aplicados por el revisor

### 1. `5eef1b9` — Zombie features en fixture `test_frontier_ai_profile_prioritises_differentiation_and_vitality`

**Archivo:** `tests/test_scoring_engine.py:126-127`.

Codex actualizó el primer fixture de presencia en el test principal, pero olvidó el segundo. El bloque seguía con `ai_visibility` y `directory_listings` (features eliminadas). El test pasaba porque `ScoringEngine` aplica neutral `50` a features ausentes, así que el runner no se quejaba — pero el fixture perdía intención: el 20.0 diseñado para `directory_presence` era ignorado y sustituido por 50 neutro.

Fix: reemplazar las 2 keys viejas por una sola `directory_presence` con valor 20.0, manteniendo la intención del diseño. El test sigue pasando y ahora evalúa lo que el autor pretendía.

Tipo: referencia zombi (regla #6 del review brief). Fix trivial.

## Bloqueantes restantes

Ninguno.

## Advertencias

### A1. Codex reportó falso positivo sobre `test_learning.py` y `test_main_experiment.py`

`REVIEW_NOTES.md` afirma que esos dos archivos fallan con `ModuleNotFoundError: No module named 'main'`. **No es regresión ni fallo real**: es un artefacto de correr `pytest` sin `PYTHONPATH=.`. Con el invocador correcto (`PYTHONPATH=. pytest` o con el paquete instalado vía `pip install -e .` en `.venv`), los 22 tests pasan tanto en `main` como en `refactor/presencia` (22 passed confirmado).

No bloquea merge. Sugerencia fuera de scope: añadir `pythonpath = ["."]` en `[tool.pytest.ini_options]` de `pyproject.toml`, o documentar el invocador en `README`.

### A2. `raw_value` como `dict` nativo vs JSON string

Codex eligió devolver `raw_value` como `dict` nativo (ver `REVIEW_NOTES.md` D1), mientras que Vitalidad (ya en main) serializa a JSON string porque `FeatureValue.raw_value` está tipado como `Optional[str]`. Es una decisión de diseño, no un bug, pero **se divergen los dos patrones** dentro del mismo engine. Los consumidores downstream (`SQLiteStore`, frontend) van a tener que manejar los dos formatos.

No bloquea merge (ambos enfoques funcionan runtime), pero conviene decidir en banda: o se cambia `FeatureValue.raw_value` a `Any` y se unifican ambas dimensiones en dict, o se fuerza JSON string también en Presencia. Queda flaggeado para el humano si quiere coherencia cross-dimensional.

## Tests

```
124 passed in 2.41s
```

Suite completa ejecutada tras el fix. Archivos focales (`test_feature_extractors.py`, `test_scoring_engine.py`) con 67 tests + resto del suite 57 tests.

### Cumplimiento del prompt verificado

- ✅ 4 features con nombres exactos: `web_presence`, `social_footprint`, `search_visibility`, `directory_presence` (`dimensions.py:152-167`, `presencia.py:158-161`).
- ✅ Pesos `0.30 / 0.35 / 0.25 / 0.10`. Suman 1.0 (assert en `dimensions.py` pasa en import).
- ✅ `ai_visibility` eliminada como feature independiente; lógica absorbida en `search_visibility` (`presencia.py:398-414`).
- ✅ `directory_listings` renombrado a `directory_presence`.
- ✅ `raw_value` estructurado (dict) en las 4 features.
- ✅ `PresenciaExtractor.__init__` sin argumento `llm` (`presencia.py:23-24`).
- ✅ Regla `marca_fantasma` en `engine.py:70, 83-85, 99-100` sigue usando `web_presence` y `social_footprint` sin cambios; `test_presence_ghost_brand_rule_caps_score` actualizado con los nuevos nombres y pasa.
- ✅ Matemáticas del assert `presencia.score == 76.25` verificadas a mano: `0.30*90 + 0.35*75 + 0.25*80 + 0.10*30 = 76.25` ✓.
- ✅ `brand_service.py` sigue instanciando `PresenciaExtractor()` sin cambios (no aparece en el diff vs main).

### Bugs potenciales revisados, descartados

- `exa.mentions[:3]`, `exa.ai_visibility_results[:5]`: safe por `field(default_factory=list)` en `ExaData`.
- División por cero: `_search_visibility` y `_social_footprint` no dividen; sumas ponderadas con constantes, sin denominadores derivados de input.
- `max([])` / slicing fuera de rango: no encontrado. Todos los slicings son `[:3]` y `[:5]`, safe aun con listas vacías.

## Notas cualitativas

- Evidencia literal preservada: `search_visibility.raw_value.evidence` lista 3 resultados con `{url, title, snippet}` (`presencia.py:422-430`). `directory_presence` emite listas explícitas de dominios encontrados por tier. Útil para conversación comercial.
- `social_footprint` sin `SocialData` degrada a score 15 + `reason=no_social_data` en lugar de ceros silenciosos. Bien para el producto.
- `_parse_last_post_days_ago` es defensivo ante strings vagos tipo "3 days ago" o fechas estructuradas. Bug edge-case leve: devuelve 0 para cualquier cantidad de "hours ago" (no amortigua 23h vs 1h), pero es lo bastante granular para el uso. Decisión de diseño, no bug.

---

**Branch:** `refactor/presencia`
**Último commit:** `5eef1b9`
**Base:** `main` (Vitalidad ya en main)

# Review report — Dimensión Coherencia

## Resumen ejecutivo

- **Decisión**: APPROVE
- **Fixes aplicados**: 1
- **Bloqueantes**: 0
- **Advertencias**: 2

## Fixes aplicados

- `1192e68` — degradé `confidence` en `tone_consistency` cuando `examples` llega con shape malformada y se filtra por completo ([src/features/coherencia.py](/Users/gsus/Antigravity/Brand3/brand3/src/features/coherencia.py:90), [src/features/coherencia.py](/Users/gsus/Antigravity/Brand3/brand3/src/features/coherencia.py:434)). Antes solo degradaba si `gap_signal != "none"`, así que una respuesta LLM con evidencia rota podía quedar con `confidence=0.85`.

## Bloqueantes restantes

Ninguno.

## Advertencias

### A1. El prompt original no está en el repo, así que el cumplimiento literal no puede verificarse al 100%

No encontré `brand3-coherencia-implement-claudecode.md` ni variantes cercanas en el workspace. Pude verificar el estado final del código contra los requisitos listados en tu brief actual, pero no cerrar una auditoría línea por línea contra el prompt original del implementador.

### A2. La cobertura de tests de Coherencia aún deja huecos en contratos LLM negativos

Los tests cubren bien `messaging_consistency` con `verdict` inválido y `gaps` malformados, pero no encontré un test explícito para:
- `messaging_consistency` con `verdict="unclear"`
- `tone_consistency` con `gap_signal` inválido
- `tone_consistency` con `examples` no-lista o items malformados

No es bloqueante porque el código ahora maneja parte de ese path, pero sigue siendo un hueco de regresión.

## Tests

- `PYTHONPATH=. ./.venv/bin/pytest -v` → **132 passed**
- `PYTHONPATH=. ./.venv/bin/pytest tests/test_feature_extractors.py tests/test_scoring_engine.py -v` → **75 passed**

Verificación focal de Coherencia:
- `dimensions.py` declara exactamente `visual_consistency`, `messaging_consistency`, `tone_consistency`, `cross_channel_coherence` con pesos `0.25 / 0.40 / 0.20 / 0.15`.
- `raw_value` de las 4 features sale como dict nativo en [src/features/coherencia.py](/Users/gsus/Antigravity/Brand3/brand3/src/features/coherencia.py).
- `coherencia_llm.py` no existe.
- `CoherenciaExtractor` acepta `llm`, `visual_analyzer`, `skip_visual_analysis`.
- `brand_service.py` instancia `CoherenciaExtractor(llm=llm, skip_visual_analysis=skip_visual_analysis)`.
- `LLMAnalyzer` conserva `analyze_coherence` y añade `analyze_messaging_consistency` y `analyze_tone_consistency`.
- `test_weighted_average_and_composite_score` está matemáticamente correcto:
  `coherencia = 0.25*80 + 0.40*60 + 0.20*70 + 0.15*50 = 65.5`
  y el composite `69.2` también cuadra con los pesos de dimensión actuales.

## Notas cualitativas

- `messaging_consistency` preserva evidencia útil para conversación comercial: `self_category`, `third_party_category`, `aligned_themes`, `gaps`, `reasoning`.
- `tone_consistency` conserva citas literales en `examples`, pero el contrato usa `gap_signal` en vez de `verdict`. Como el prompt original no está disponible, lo dejo como observación y no como fallo literal.
- Los fallbacks heurísticos de Coherencia devuelven razones y señales accionables; no son solo scores neutrales mudos.
