# REVIEW NOTES — Rediseño Percepción

**Branch:** `refactor/percepcion`
**Scope:** última dimensión del refactor. Single-file + LLM-first + dict `raw_value`.

## Archivos modificados

1. `src/features/percepcion.py` — reescritura completa. 4 features (`brand_sentiment`, `mention_volume`, `sentiment_trend`, `review_quality`) con `raw_value` dict nativo.
2. `src/features/percepcion_llm.py` — **eliminado**.
3. `src/features/llm_analyzer.py` — añadido `analyze_brand_sentiment`. `analyze_sentiment` se conserva.
4. `src/dimensions.py` — bloque `percepcion` actualizado: 4 features con pesos `0.40 / 0.25 / 0.20 / 0.15`. `controversy_flag` eliminada como feature. Rule `controversia_activa` eliminada de la lista (el cap se aplica ahora dentro de `brand_sentiment`).
5. `src/scoring/engine.py` — rule `controversia_activa` eliminada del `_build_rules` y del return dict. `sin_datos_suficientes` se mantiene.
6. `src/services/brand_service.py` — `PercepcionLLMExtractor` sustituido por `PercepcionExtractor(llm=llm)`.
7. `tests/test_feature_extractors.py` — `PercepcionExtractorTests` reescrita: 14 tests nuevos cubriendo LLM happy path, controversia capping, verdict inválido, evidence malformada, `controversy_detected` no-bool, fallback sin LLM, tier heurístico de `mention_volume` y señal de `review_quality`.
8. `tests/test_scoring_engine.py` — fixtures actualizados (`brand_sentiment` en lugar de `sentiment_score` + `controversy_flag`); assert de composite recalculado a 70.9.

## Decisiones de implementación

### D1. `brand_sentiment` absorbe `controversy_flag` y aplica el cap dentro de la feature

Antes el cap a 35 por controversia estaba en una rule del `ScoringEngine` que leía `controversy_flag.value > 70`. Ahora el LLM devuelve `controversy_detected: bool` y la feature aplica `min(score, 35)` internamente. La rule del engine queda eliminada. Razón: mantiene el cap pero lo ata a la señal LLM concreta (más precisa que keyword matching) sin depender de una rule cross-feature que puede quedar inconsistente.

### D2. Rule `controversia_activa` eliminada, `sin_datos_suficientes` conservada

Solo eliminé la rule cuyo cap ya está dentro de la feature. `sin_datos_suficientes` depende de `mention_volume`, una señal estructural independiente — tiene sentido que siga siendo una rule del engine (si no hay datos, el score es neutral cualquiera sea el sentiment).

### D3. `sentiment_trend` LLM-first con dos llamadas

Cuando hay LLM disponible y ≥4 menciones con fecha parseable, se corre `analyze_brand_sentiment` sobre cada mitad (older/newer) y se comparan los `sentiment_score` devueltos. Delta > 5 → "improving"; delta < -5 → "declining"; resto → "stable". Cuesta 2 llamadas LLM extra por análisis — el prompt lo pide explícitamente. Fallback heurístico normalizado si falla cualquiera de las dos llamadas.

### D4. Fallback heurístico normalizado por total de palabras

Antes `_sentiment_score` usaba `pos_count / (pos_count + neg_count)` — ratio entre señales detectadas pero no densidad. Ahora: `net = pos_ratio - neg_ratio` (cada uno dividido por total de palabras), comprimido a `50 + max(-50, min(50, net*5000))`. Evita que una web muy larga con pocos marcadores se escore como "neutro alto". Mismo patrón en `sentiment_trend` heurístico.

### D5. Validación estricta del output LLM

Patrón ya establecido en las otras dimensiones:
- `verdict` fuera del enum → fallback total con `reason="llm_invalid_verdict"`.
- `sentiment_score` no numérico → `reason="llm_invalid_response"`.
- `controversy_detected` no-bool → tratado como `false` con warning explícito en `raw_value.controversy_detected_type_warning` (no fallback total — es campo accesorio).
- `evidence` no-lista o items malformados → filtrados por `_clean_sentiment_evidence`; si queda vacía y verdict ≠ "unclear" y había datos → confidence degradada a 0.5 con `reason="llm_partial_evidence"`.

### D6. `mention_volume` y `review_quality` con dict estructurado

- `mention_volume.raw_value` incluye `volume_tier` (enum) y `top_domains` (top 3). Útil para ventas ("vuestra cobertura viene mayoritariamente de TechCrunch y The Verge").
- `review_quality.raw_value` separa `has_professional_reviews` (G2, Trustpilot, Capterra…) de `has_consumer_reviews` (Yelp, app stores) y devuelve `platforms_with_reviews[{domain, count, sample_urls}]`. Se puede decir: "aparecéis en G2 con 3 reviews, nada en Trustpilot".

## Tests

**Eliminados** (4 antiguos con assertions sobre strings en raw_value).

**Añadidos** (14 nuevos): cobertura para los 4 features, happy path LLM, controversy cap, verdict inválido, evidence malformada, `controversy_detected` no-bool, fallbacks sin LLM, tiers, signals.

Helper de test: `_make_llm(sentiment_payload, older_payload, newer_payload, sequence)`.

## Resultado

```
143 passed in 1.28s
```

## Verificaciones manuales pendientes

1. **Prompt de `analyze_brand_sentiment`**: pide distinguir crítica ordinaria de controversia seria. En producción puede requerir ajuste — el umbral es subjetivo.
2. **Coste operativo de `sentiment_trend`**: 2 llamadas LLM extra por análisis. En benchmarks grandes puede ser relevante; considerar flag para omitir trend en modo benchmark (fuera de scope).
3. **Learning system sigue buscando `sentiment_score` y `controversy_flag`** (nombres viejos) en `src/learning/`. Mismo patrón dormido que Diferenciación. Fuera de scope; se re-enganchará cuando se retome el learning.

## Fuera de scope

- Collectors, learning, versioning, SQLiteStore no se tocan.
- Otras 4 dimensiones ya mergeadas no se tocan.
- `AuthenticityAnalyzer` intacto.
