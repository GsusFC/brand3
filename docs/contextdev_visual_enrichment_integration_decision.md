# Context.dev Visual Enrichment Integration Decision

Date: 2026-06-02

## Veredicto

Hay un mejor enfoque disponible: Context.dev debe entrar en Brand3 como una
capa controlada de enriquecimiento visual y de personalidad, no como proveedor
principal del Research Pack.

## Decision

Las senales visuales de Context.dev pueden enriquecer
`BrandResearchPack.visual_or_conceptual_signals` despues de normalizacion
semantica.

El enriquecimiento es experimental y queda desactivado por defecto mediante:

```text
BRAND3_CONTEXTDEV_VISUAL_ENRICHMENT=false
```

## Uso Permitido

Las senales de identidad visual de Context.dev pueden apoyar:

- `personality`
- `brand_idea`
- `attributes`

Deben describir como se expresa la marca visual y conductualmente.

## Uso No Permitido

Las senales de identidad visual de Context.dev no deben sostener por si solas:

- `core_purpose`
- `mission`
- `value_proposition`
- `values`

Esos bloques necesitan evidencia textual, conductual o claims explicitos del
Research Pack.

## Politica De Promocion

Comportamiento actual del gate:

- `visual_colors`, `visual_typography`, `visual_components`, `visual_fonts`
  son promocionables solo despues de normalizacion.
- `entity_resolution` e `industry_classification` requieren revision.
- screenshots e image URLs requieren revision hasta que exista un contrato de
  evidencia visual.
- los candidatos de producto quedan como material de review. No deben alimentar
  automaticamente el TLDR en el modo recomendado de validacion.

## Modo Recomendado De Validacion

El modo recomendado para seguir probando Context.dev es:

```text
mode=visual_only
```

Este modo mantiene la evaluacion completa de candidatos, pero solo aplica al
Research Pack las senales visuales normalizadas. Excluye automaticamente
`research_pack.product_summary` y las confidence notes derivadas de candidatos
de producto.

## Resumen De Validacion Inicial

La run `154` de LangChain se uso como caso local real.

Los payloads visuales crudos de Context.dev mejoraban `personality`, pero
hacian que Analyst Pass dependiera de menos fuentes de evidencia.

Despues de normalizacion semantica:

```text
original_detected=9
enriched_detected=9
evidence_delta=-1
```

La mejora mas clara aparecio en el bloque `personality`, donde Analyst Pass uso
la senal visual normalizada para describir una marca tecnica, moderna y de alto
control.

## Benchmark Multi-Caso

El 2026-06-03 se valido Context.dev sobre cinco marcas reales de la base local:

- LangChain, run `154`
- SigmaOS, run `152`
- Bokeroon, run `155`
- Galtea, run `156`
- WeAreFLOC, run `159`

Context.dev devolvio datos para todas las capacidades probadas:

```text
cases=5
successful_capabilities=30
failed_capabilities=0
candidates=60
promotable=36
review_required=24
blocked=0
```

Se compararon dos variantes del Analyst Pass:

- `full`: aplica visual identity y candidatos de producto promocionables.
- `visual_only`: aplica solo visual identity normalizada.

Resultado por marca:

```text
LangChain   full +2 evidence | visual_only  0 evidence
SigmaOS     full -1 evidence | visual_only -2 evidence
Bokeroon    full +1 evidence | visual_only  0 evidence
Galtea      full -4 evidence | visual_only +1 evidence
WeAreFLOC   full +6 evidence | visual_only  0 evidence
```

Resultado agregado:

```text
full        changed_blocks=42 evidence_delta=+4 review_delta=-3
visual_only changed_blocks=42 evidence_delta=-1 review_delta=-5
```

Interpretacion:

- `full` aumenta mas la evidencia agregada, pero introduce riesgo claro por
  candidatos de producto, especialmente en Galtea.
- `visual_only` reduce mas las recomendaciones de revision humana y evita la
  degradacion fuerte de Galtea.
- Ninguna variante justifica todavia activacion automatica en produccion.
- La evidencia mas consistente de Context.dev sigue estando en personalidad,
  tono visual, atributos y expresion conceptual.

## Fuera De Alcance

- No hay integracion runtime de produccion en este paso.
- No se reemplaza `EvidenceGraph`.
- No se reemplaza `BrandResearchPack`.
- No hay promocion automatica de screenshots/images.
- No hay resolucion automatica de entidad desde Context.dev.
- No hay cambios automaticos de mission o value proposition desde evidencia
  visual.
- No hay promocion automatica de candidatos de producto al TLDR.

## Siguiente Paso

Si esto avanza hacia integracion runtime, el primer corte debe seguir siendo un
path shadow-only que registre:

- senales visuales normalizadas de Context.dev,
- decisiones de promocion,
- delta generado del dry-run Research Pack,
- resultado de la comparacion TLDR A/B.

No deberia alterar el TLDR visible para usuarios hasta que un benchmark
multi-caso demuestre mejora neta de calidad.
