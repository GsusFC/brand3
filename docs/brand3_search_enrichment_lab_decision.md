# Brand3 Search Enrichment Lab Decision

## Veredicto

La mejora de busqueda y enriquecimiento de fuentes debe desarrollarse como proyecto separado tipo Lab antes de integrarse en el pipeline principal.

No se debe promover un nuevo proveedor, un nuevo flujo de busqueda o una capa de research adicional a produccion solo porque entregue mas resultados. La integracion solo tiene sentido si demuestra mejoria medible y viabilidad economica.

## Decision

Brand3 mantendra el pipeline actual como flujo canonico.

El Lab puede ser online y usar proveedores reales, APIs externas y casos vivos. La restriccion no es que sea offline; la restriccion es que este aislado de Brand3 productivo.

Las mejoras de busqueda en internet se evaluaran en un Lab separado, con outputs comparables y sin alimentar automaticamente:

- scoring
- TLDR
- Brand Research Pack canonico
- resultados publicos
- API productiva

El Lab podra usar nuevos proveedores, nuevas queries, nuevos contratos de source inventory y nuevas estrategias de adquisicion, pero sus resultados permaneceran en modo shadow hasta superar criterios de promocion.

Mientras este en Lab, no debe modificar:

- rutas publicas existentes
- scoring actual
- Magnetism Scanner canonico
- Brand Audit canonico
- Research Pack canonico
- API productiva
- base de datos productiva salvo tablas o namespaces claramente experimentales

## Hipotesis a validar

El Lab existe para comprobar si busqueda/enriquecimiento adicional mejora realmente:

- resolucion de entidad
- descubrimiento de superficies owned
- cobertura de paginas importantes
- deteccion de parent/product/sub-brand
- calidad de contexto externo
- deteccion de competidores
- visibilidad AI
- reduccion de colisiones de entidad
- utilidad del Research Pack
- calidad final del TLDR

Tambien debe medir si esa mejora compensa el coste.

## Criterios minimos de promocion

Una mejora solo deberia integrarse si cumple estas condiciones:

1. Mejora la calidad frente al baseline actual en un benchmark representativo.
2. Reduce o no aumenta de forma significativa el ruido y las colisiones de entidad.
3. Produce fuentes trazables, no solo resumenes generados.
4. Puede normalizarse al contrato interno de fuentes.
5. Tiene coste por evidencia util asumible.
6. No aumenta demasiado latencia ni tasa de fallos.
7. Mantiene separacion entre evidencia owned, externa, competidor, shadow y noise.
8. Tiene tests de regresion para casos ambiguos.

## Metricas recomendadas

El Lab debe reportar, por caso y por proveedor:

- `entity_resolution_accuracy`
- `owned_surface_recall`
- `critical_page_coverage`
- `external_context_precision`
- `competitor_context_precision`
- `noise_rate`
- `entity_collision_rate`
- `requires_human_review_rate`
- `cost_per_case`
- `cost_per_valid_source`
- `latency_ms`
- `failure_rate`
- `tldr_quality_delta`

## Proveedores candidatos

El Lab puede evaluar, como minimo:

| Proveedor | Variable | Rol candidato |
| --- | --- | --- |
| Exa | `EXA_API_KEY` | Baseline actual para busqueda semantica, menciones, competidores, news y AI visibility. |
| Firecrawl | `FIRECRAWL_API_KEY` | Baseline actual para scraping; candidato para map/crawl/extract mas sistematico. |
| Parallel | `PARALLEL_API_KEY` | Shadow research y segunda opinion con objetivos por intent. |
| Tavily | `TAVILY_API_KEY` | Search/extract/crawl/map orientado a agentes. |
| Linkup | `LINKUP_API_KEY` | Busqueda y extraccion orientada a AI/RAG. |
| Brave Search API | `BRAVE_SEARCH_API_KEY` | Indice web independiente y contexto compacto para LLM. |
| SerpApi | `SERPAPI_API_KEY` | SERP real como fallback para visibilidad de mercado. |
| Perplexity Sonar | `PERPLEXITY_API_KEY` | Descubrimiento de fuentes citadas; sus respuestas no deben ser evidencia final. |
| Context.dev | `CONTEXT_DEV_API_KEY` | Proveedor experimental ya usado en scripts de visual/context enrichment. |
| Tinyfish | `TINYFISH_API_KEY` | Proveedor experimental ya usado en probes/fetch scripts. |

Cada proveedor debe adaptarse al mismo contrato interno. No se compararan por volumen bruto de resultados, sino por evidencia util, coste y seguridad de entidad.

### Variantes Exa deep

El Lab puede evaluar los modos de `/search` de Exa como variantes separadas del proveedor base:

| Variante Lab | `type` Exa | Uso candidato |
| --- | --- | --- |
| `exa` | `fast` | Baseline historico del Lab; baja latencia y buena evidencia inicial. |
| `exa-fast` | `fast` | Alias explicito via endpoint `/search`; recomendado para comparar coste contra otros modos. |
| `exa-auto` | `auto` | Router equilibrado de Exa; util para saber si mejora el baseline sin subir demasiado latencia. |
| `exa-deep-lite` | `deep-lite` | Primera prueba deep razonable: sintesis ligera, latencia moderada y menor riesgo de coste. |
| `exa-deep` | `deep` | Multi-step search para casos ambiguos o con parent/product/sub-brand. |
| `exa-deep-reasoning` | `deep-reasoning` | Solo para casos dificiles y presupuestados; no debe ejecutarse por defecto. |

Regla de coste:

- Los modos deep no entran en la seleccion por defecto aunque `EXA_API_KEY` exista.
- Solo se ejecutan si se piden explicitamente con `--providers`.
- La evidencia final sigue siendo la URL/fuente devuelta, no el texto sintetizado.
- Si Exa devuelve `output.grounding` o `costDollars.total`, el Lab lo guarda como diagnostics/coste, pero no lo promociona automaticamente a evidencia canonica.
- Para comparativas economicas entre modos Exa, preferir `exa-fast` frente a `exa`, porque `exa-fast` llama directamente a `/search` y captura `costDollars.total` cuando esta disponible.

Regla de seleccion:

- Si la key de un proveedor esta presente en `.env`, el proveedor entra en el Lab.
- Si la key falta o esta vacia, el proveedor se considera descartado para ese ciclo.
- La falta de key no debe tratarse como error salvo que el usuario haya pedido explicitamente evaluar ese proveedor.
- Context.dev se considera interesante para identidad y Visual Signature, pero queda inactivo mientras el coste o la falta de creditos gratuitos no justifique probarlo.

Exclusion explicita:

- Google Search directo y Gemini Deep Research quedan fuera del Lab de adquisicion por ahora.
- Esta exclusion no significa eliminar Gemini como LLM de analisis si ya esta configurado en Brand3.
- La razon es mantener el Lab centrado en proveedores que devuelvan fuentes normalizables, coste medible y resultados comparables por caso.
- Si mas adelante se evalua Deep Research, deberia entrar como experimento separado y sus resumenes no deberian tratarse como evidencia final sin URLs/fuentes trazables.

## Contrato recomendado

Todo resultado del Lab deberia normalizarse como `BrandSourceObservation`:

```text
provider
query_intent
source_role
url
title
excerpt
published_at
source_class
relation_to_entity
confidence
freshness
extraction_eligible
requires_human_review
cost_estimate
latency_ms
diagnostics
```

Y agregarse despues en un `BrandSourceInventory`:

```text
required_channels
observed_channels
missing_channels
blocked_channels
ambiguous_sources
noise_sources
evidence_eligible_sources
provider_diagnostics
cost_summary
```

## Integracion futura

La integracion con Brand3 principal solo deberia ocurrir cuando el Lab produzca evidencia suficiente de mejora.

Orden sugerido:

1. Lab aislado con fixtures, casos historicos y, si conviene, llamadas online reales.
2. Shadow runs en scans reales sin afectar resultados canonicos.
3. Comparativa Exa actual vs nuevos proveedores.
4. Revision de coste por evidencia util.
5. Decision explicita de promocion o descarte.
6. Promocion limitada por canal, no por proveedor completo.
7. Integracion gradual en Research Pack solo tras aprobar la promocion.
8. Exposicion controlada en API/UI solo despues de integracion.

## Runner inicial

El runner online aislado vive en:

```text
scripts/search_enrichment_lab.py
```

Uso basico:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py
```

Por defecto:

- lee keys desde `.env`
- descarta proveedores sin key o con placeholder
- ejecuta casos pequenos por defecto
- escribe artefactos bajo `out/search_enrichment_lab/<timestamp>/`
- no toca Brand3 canonico
- no escribe en la base de datos productiva

Para limitar gasto durante pruebas:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py \
  --providers exa,brave,tavily \
  --results 1 \
  --max-cases 1 \
  --max-queries 1
```

Para comprobar proveedores activos sin llamadas de red:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py --list-providers
```

Para estimar llamadas antes de ejecutar proveedores:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py \
  --cases-file examples/benchmarks/search_enrichment_lab/cases.json \
  --providers exa,brave,tavily,parallel \
  --results 2 \
  --max-cases 5 \
  --max-queries 3 \
  --plan-only
```

Para probar Exa deep con presupuesto minimo:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py \
  --cases-file examples/benchmarks/search_enrichment_lab/cases.json \
  --providers exa-fast,exa-auto,exa-deep-lite \
  --results 1 \
  --max-cases 1 \
  --max-queries 1 \
  --timeout 45 \
  --plan-only
```

Si el plan es aceptable, retirar `--plan-only`:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py \
  --cases-file examples/benchmarks/search_enrichment_lab/cases.json \
  --providers exa-fast,exa-auto,exa-deep-lite \
  --results 1 \
  --max-cases 1 \
  --max-queries 1 \
  --timeout 45
```

`exa-deep` y `exa-deep-reasoning` deberian reservarse para pasadas pequenas, con una hipotesis concreta y comparando coste por fuente valida. No son candidatos a ejecutarse en el camino normal del Lab hasta demostrar mejora clara.

Para usar casos propios:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py \
  --cases-file path/to/cases.json \
  --results 2
```

Formato de casos:

```json
{
  "cases": [
    {"brand": "LangChain", "url": "https://www.langchain.com"},
    {"brand": "ChatGPT", "url": "https://chatgpt.com"}
  ]
}
```

## Regla final

Mas busqueda no es automaticamente mejor research.

Solo se integra lo que aumente evidencia util, reduzca ambiguedad y mantenga coste operativo razonable.
