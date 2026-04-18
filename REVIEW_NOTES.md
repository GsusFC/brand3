# REVIEW NOTES — Rediseño Diferenciación

**Branch:** `refactor/diferenciacion`
**Scope:** refactor completo de la dimensión `diferenciacion` siguiendo el patrón single-file y `raw_value` estructurado ya usado en Vitalidad y Presencia.

## Archivos modificados

1. `src/features/diferenciacion.py` — reescritura completa a 5 features con dos paths LLM-first y fallbacks heurísticos.
2. `src/features/diferenciacion_llm.py` — eliminado; la lógica LLM quedó absorbida en `diferenciacion.py`.
3. `src/features/llm_analyzer.py` — añadidos `analyze_positioning_clarity` y `analyze_uniqueness`.
4. `src/dimensions.py` — bloque `diferenciacion` actualizado a pesos `0.30 / 0.25 / 0.20 / 0.15 / 0.10`.
5. `src/scoring/engine.py` — rule `lenguaje_generico` adaptada para usar `uniqueness`.
6. `src/services/brand_service.py` — wiring actualizado para usar `DiferenciacionExtractor(llm=llm)`.
7. `tests/test_feature_extractors.py` — tests viejos sustituidos por cobertura de las 5 features nuevas y validación LLM.
8. `tests/test_scoring_engine.py` — fixtures y expected values recalculados con los nombres/pesos nuevos.

## Decisión sobre la rule rename

Se eligió **Opción B**.

Mantengo el nombre `lenguaje_generico` en `src/scoring/engine.py` y en `src/niche/profiles.py` sin cambios de nombres. La condición ahora capea cuando `uniqueness < (100 - threshold)`.

Razón:
- minimiza conflictos con el trabajo paralelo de Coherencia;
- evita tocar `src/niche/profiles.py`;
- conserva la semántica práctica de la regla sin introducir una migración de nombres innecesaria.

## Decisiones de implementación no obvias

### D1. `positioning_clarity` valida `verdict` y evidencia por separado

La validación estricta sigue el patrón de `momentum`:
- `verdict` fuera del enum => fallback total con `reason="llm_invalid_verdict"`;
- `evidence` malformada o vacía => se conserva `source="llm"` pero baja `confidence` a `0.5` y se marca `reason="llm_partial_evidence"`.

### D2. `uniqueness` fallback normalizado por longitud

El fallback ya no usa conteo bruto de frases genéricas. Ahora calcula `ratio = generic_hits / sentence_count`, y desde ahí mapea el score, para no castigar textos largos por volumen absoluto.

### D3. `content_authenticity` y `brand_personality` conservan el score del analyzer pero no su `raw_value`

No toqué `src/features/authenticity.py`. En su lugar, `diferenciacion.py` reutiliza sus scores y construye `raw_value` dict estructurado encima:
- `content_authenticity`: `ai_pattern_hits`, `structural_hits`, `uniformity_penalty`, `authenticity_verdict`, `evidence_snippets`
- `brand_personality`: `personality_score`, `signals_detected`, `corporate_signals_count`, `verdict`

### D4. `competitor_distance` prioriza `CompetitorData`

Cuando hay `competitor_data.comparisons`, la feature devuelve `source="competitor_web_comparison"` con resumen estructurado:
- `avg_distance`
- `closest_competitor`
- `most_different`
- `competitors_analyzed`
- `brand_unique_terms`
- `similarity_threshold_crossed`

Si no hay comparaciones, cae a un fallback neutral con `raw_value` dict, no string.

## Tests añadidos vs eliminados

### Eliminados / sustituidos

- Tests de `unique_value_prop`.
- Tests de `generic_language_score`.
- Tests de `brand_vocabulary` como feature independiente.

### Añadidos

`positioning_clarity`
- `test_positioning_clarity_without_llm_uses_heuristic_fallback`
- `test_positioning_clarity_with_llm_uses_structured_output`
- `test_positioning_clarity_invalid_verdict_falls_back`
- `test_positioning_clarity_malformed_evidence_degrades_confidence`

`uniqueness`
- `test_uniqueness_without_llm_uses_normalized_ratio_fallback`
- `test_uniqueness_with_llm_uses_structured_output`
- `test_uniqueness_invalid_verdict_falls_back`

`competitor_distance`
- `test_competitor_distance_uses_structured_raw_value`

`content_authenticity` / `brand_personality`
- `test_content_authenticity_and_brand_personality_return_structured_raw_value`

`scoring`
- fixtures y expected values recalculados en `test_weighted_average_and_composite_score`
- fixture de rule override actualizada para `uniqueness`

## Warnings no bloqueantes

1. La suite completa con `./.venv/bin/pytest -v` falla en collection fuera del scope del refactor por `ModuleNotFoundError: No module named 'main'` en `tests/test_learning.py` y `tests/test_main_experiment.py`.
2. En este workspace hay cambios paralelos de Coherencia sin commit (`src/features/coherencia.py`, eliminación de `src/features/coherencia_llm.py`). No los toqué ni los incluí en el commit de Diferenciación.
3. El entorno local no tiene `firecrawl`, así que para la verificación dirigida con `unittest` tuve que stubear ese módulo en memoria.

## Verificaciones realizadas

1. `python3 -m py_compile` sobre los archivos modificados por Diferenciación: OK.
2. `./.venv/bin/pytest tests/test_feature_extractors.py tests/test_scoring_engine.py -v`:
   falló inicialmente porque la rama aún tenía wiring viejo y expected values obsoletos; eso quedó corregido después.
3. `./.venv/bin/pytest -v`:
   interrumpido por collection errors fuera de scope (`import main`).
4. `python3 -m unittest` con stub de `firecrawl` sobre:
   - `DiferenciacionExtractorTests`
   - `ScoringEngineTests`
   Resultado: **16 tests OK**.
5. Verificación manual de `DiferenciacionExtractor().extract(None, None, None)` con stub de `firecrawl`:
   no crashea, devuelve las 5 features y todos los `raw_value` son dict.
