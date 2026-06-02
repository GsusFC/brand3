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
- los candidatos de producto quedan como material de review/confidence-note
  salvo que `product_summary` este vacio.

## Resumen De Validacion

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

## Fuera De Alcance

- No hay integracion runtime de produccion en este paso.
- No se reemplaza `EvidenceGraph`.
- No se reemplaza `BrandResearchPack`.
- No hay promocion automatica de screenshots/images.
- No hay resolucion automatica de entidad desde Context.dev.
- No hay cambios automaticos de mission o value proposition desde evidencia
  visual.

## Siguiente Paso

Si esto avanza hacia integracion runtime, el primer corte deberia ser un path
shadow-only que registre:

- senales visuales normalizadas de Context.dev,
- decisiones de promocion,
- delta generado del dry-run Research Pack,
- resultado de la comparacion TLDR A/B.

No deberia alterar el TLDR visible para usuarios hasta que un benchmark
multi-caso demuestre mejora neta de calidad.
