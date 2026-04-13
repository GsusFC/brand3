# Benchmark Validation

## Objetivo

Validar cambios de scoring con un flujo repetible y sin contaminar la base local de trabajo.

Este documento es el runbook recomendado para:

- correr benchmark en entorno sano
- comparar before/after
- interpretar resultados sin mezclar problemas de red con cambios reales de scoring

## Requisitos

Antes de confiar en el benchmark:

- Exa debe responder
- Firecrawl debe devolver contenido real
- el entorno no debe estar degradado por DNS o timeouts persistentes

Si no se cumple eso, el benchmark mide el entorno, no el scoring.

## Regla

Cada benchmark debe correrse contra una DB temporal.

No reutilizar una SQLite anterior para comparar scoring.

## Ejecución mínima

Desde la raíz del repo:

```bash
scripts/run_benchmark_validation.sh examples/startup_benchmark.json
```

Con perfiles explícitos:

```bash
scripts/run_benchmark_validation.sh examples/startup_benchmark.json base,frontier_ai,enterprise_ai,physical_ai
```

El script:

- crea una DB temporal en `/tmp`
- desactiva caché
- ejecuta `main.py benchmark`
- deja el JSON del benchmark en `output/benchmarks/`

## Comparar dos benchmarks

```bash
/Users/gsus/brand3-scoring/.venv/bin/python main.py benchmark-compare \
  --before output/benchmarks/OLD.json \
  --after output/benchmarks/NEW.json
```

Salida:

- JSON de comparación en `output/benchmarks/`
- deltas por variante
- deltas por marca
- cambios en `niche_match` y `subtype_match`

## Qué mirar

### 1. Salud del entorno

Antes de interpretar scoring:

- ¿hay `web chars > 0`?
- ¿hay menciones de Exa?
- ¿hay noticias?
- ¿la clasificación de nicho tiene evidencia razonable?

Si no, detener ahí.

### 2. Deltas por variante

Mirar en `summary.variant_deltas`:

- `average_composite_delta`
- `niche_match_improved`
- `niche_match_worsened`
- `subtype_match_improved`
- `subtype_match_worsened`

### 3. Deltas por marca

Mirar:

- `composite_delta`
- `dimension_deltas`

Especialmente:

- `percepcion`
- `diferenciacion`

porque `Sprint A` afecta sobre todo a esas zonas y a reglas de coherencia/presencia.

## Cómo interpretar Sprint A

Cambios esperables:

- `sentiment_trend` más estable o neutral cuando faltan fechas
- `generic_language_score` menos agresivo en webs largas
- `coherencia` puede bajar en marcas con un solo canal realmente activo
- `ai_visibility` debería inflarse menos por simple cantidad

No esperable:

- cambios masivos uniformes en todas las marcas

Si todo cae a la vez:

- probablemente el entorno o la recogida de datos está mal

## Checklist de validación

1. correr benchmark base en entorno sano
2. guardar JSON
3. aplicar cambio de scoring
4. correr benchmark otra vez
5. comparar con `benchmark-compare`
6. revisar 3-5 marcas manualmente
7. decidir si el cambio mejora o empeora

## Qué no hacer

- no comparar benchmarks de entornos distintos como si fueran equivalentes
- no juzgar scoring si Exa o Firecrawl están rotos
- no promover calibraciones solo por una media agregada

## Siguiente nivel

Cuando la validación esté madura:

- archivar benchmarks importantes
- versionar sets de benchmark serios
- sustituir reviews abiertas por informes cerrados de cambio
