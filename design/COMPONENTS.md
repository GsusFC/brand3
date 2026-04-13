# Components

## Objetivo

Definir el sistema de componentes de Brand3 antes de implementar frontend.

Este documento no describe una librería cerrada. Describe:

- piezas reutilizables
- propósito
- variantes
- reglas de uso

## Principios

- primero marca, luego estado, luego sistema
- evitar componentes “de UI kit” sin criterio de producto
- preferir pocos componentes bien definidos a muchos intercambiables

## Capas

### Layout

- `AppShell`
- `TopNav`
- `SectionHeader`
- `PageHeader`
- `Panel`
- `SplitLayout`
- `MetricStrip`

### Identity

- `BrandAvatar`
- `BrandIdentity`
- `BrandRow`
- `BrandHero`

### Data display

- `ScoreChip`
- `DimensionCard`
- `DeltaPill`
- `StatusPill`
- `PhasePill`
- `ProfileBadge`
- `NicheBadge`
- `FingerprintBadge`

### Tables and lists

- `DataTable`
- `MobileStructuredList`
- `KeyValueList`
- `EventTimeline`

### Actions and forms

- `PrimaryButton`
- `SecondaryButton`
- `DangerButton`
- `InputField`
- `SearchField`
- `ToggleField`
- `FilterBar`

### Narrative and audit

- `InsightBlock`
- `AuditPanel`
- `EmptyState`
- `ErrorState`
- `LoadingState`

### Charts

- `ScoreTrendChart`
- `DimensionTrendChart`
- `ComparisonChart`

## Componentes principales

## 1. AppShell

Uso:

- estructura global de la app

Incluye:

- top nav
- container
- content area

Regla:

- no meter estilos de página dentro del shell

## 2. TopNav

Uso:

- navegación primaria

Items esperados:

- Analyze
- Jobs
- Brands
- Runs
- Experiments
- Calibration

Regla:

- ligera y sobria
- nunca competir con el contenido principal

## 3. PageHeader

Uso:

- introducir una pantalla

Partes:

- title
- subtitle opcional
- metadata opcional
- actions opcionales

Variantes:

- editorial
- operational
- technical

## 4. Panel

Uso:

- bloque de superficie general

Variantes:

- `default`
- `muted`
- `technical`

Regla:

- reemplaza el abuso de cards genéricas

## 5. BrandAvatar

Uso:

- logo o fallback de marca

Tamaños:

- `sm`
- `md`
- `lg`
- `xl`

Regla:

- mantener consistencia extrema de tamaño y padding

## 6. BrandIdentity

Uso:

- mostrar identidad básica de marca

Incluye:

- `BrandAvatar`
- nombre
- dominio
- metadata opcional

Variantes:

- compact
- default
- hero

## 7. BrandRow

Uso:

- filas de jobs, runs, brands

Debe poder incluir:

- identity
- status
- score o timestamp
- acción principal

Regla:

- BrandRow es patrón estructural, no solo estética

## 8. BrandHero

Uso:

- cabecera principal de brand detail

Incluye:

- avatar/logo
- nombre
- dominio
- composite
- trend
- profile
- niche

Regla:

- es uno de los componentes más importantes del producto

## 9. ScoreChip

Uso:

- score principal o parcial

Contenido:

- número
- etiqueta opcional
- delta opcional

Variantes:

- compact
- default
- large

Regla:

- no usar gauges redondos

## 10. DimensionCard

Uso:

- mostrar una dimensión del scoring

Incluye:

- nombre
- score
- descripción corta opcional
- delta opcional

Uso ideal:

- banda horizontal de dimensiones
- grid responsive en mobile

## 11. DeltaPill

Uso:

- before/after
- trends

Estados:

- positive
- neutral
- negative

Regla:

- compacta y legible

## 12. StatusPill

Uso:

- estado de job o workflow

Estados mínimos:

- queued
- running
- done
- failed
- cancelled

Regla:

- pequeña
- color semántico contenido

## 13. PhasePill

Uso:

- fase interna de job

Fases:

- collecting
- extracting
- scoring
- finalizing

Regla:

- mostrarla separada del estado

## 14. ProfileBadge

Uso:

- calibration profile

Valores:

- base
- frontier_ai
- enterprise_ai
- physical_ai

Regla:

- usar acento sutil por perfil, no saturación total

## 15. NicheBadge

Uso:

- niche y subtype

Regla:

- siempre secundaria respecto a la marca y al score

## 16. FingerprintBadge

Uso:

- identificar scoring state

Regla:

- técnica
- discreta
- útil para runs, experiments y audit

## 17. DataTable

Uso:

- tablas principales

Tablas previstas:

- jobs
- brands
- runs
- experiments
- candidates

Regla:

- no intentar resolver móvil por scroll horizontal infinito

## 18. MobileStructuredList

Uso:

- reemplazo de tabla en móvil

Cada item:

- identity arriba
- metadata agrupada
- acción principal

Regla:

- no parecer card de marketplace

## 19. KeyValueList

Uso:

- audit
- metadata
- configuración

Ideal para:

- gate config
- run metadata
- profile selection

## 20. EventTimeline

Uso:

- detalle de job

Contenido:

- phase/event
- timestamp
- note opcional

Regla:

- cronología limpia
- muy poco adorno

## 21. FilterBar

Uso:

- filtros de tablas/listados

Puede incluir:

- search
- status
- profile
- date

Regla:

- no convertirlo en un panel de filtros pesado

## 22. InsightBlock

Uso:

- fragmentos de lectura humana

Casos:

- resumen editorial
- explicación de score
- razón de selección de profile

Variantes:

- default
- warning
- technical

## 23. AuditPanel

Uso:

- mostrar contexto técnico de una run

Incluye:

- profile
- niche
- subtype
- baseline
- gate config
- fingerprint

Regla:

- ordenado y muy legible

## 24. EmptyState

Uso:

- ausencia de datos

Tipos:

- no jobs
- no brands
- no runs
- no experiments

Regla:

- sobrio
- textual
- sin ilustraciones decorativas

## 25. ErrorState

Uso:

- errores de carga o de ejecución

Debe mostrar:

- qué falló
- dónde falló
- siguiente acción posible

## 26. LoadingState

Uso:

- carga inicial
- transición de fetch

Regla:

- skeletons simples
- nada espectacular

## 27. ScoreTrendChart

Uso:

- brand detail

Muestra:

- evolución de composite

## 28. DimensionTrendChart

Uso:

- detalle histórico

Muestra:

- evolución por dimensión

## 29. ComparisonChart

Uso:

- compare runs
- experiment detail

Muestra:

- before/after
- delta

## Composición por página

### Analyze

- `PageHeader`
- `Panel`
- `InputField`
- `ToggleField`
- `PrimaryButton`
- `DataTable` o `MobileStructuredList` para jobs recientes

### Jobs

- `PageHeader`
- `FilterBar`
- `DataTable`
- `MobileStructuredList`
- `BrandRow`
- `StatusPill`
- `PhasePill`

### Job Detail

- `PageHeader`
- `BrandIdentity`
- `StatusPill`
- `PhasePill`
- `EventTimeline`
- `KeyValueList`
- `ErrorState`

### Brand Detail

- `BrandHero`
- `MetricStrip`
- `DimensionCard`
- `ScoreTrendChart`
- `InsightBlock`
- `DataTable`

### Run Detail

- `PageHeader`
- `ScoreChip`
- `ProfileBadge`
- `NicheBadge`
- `DimensionCard`
- `AuditPanel`
- `InsightBlock`

### Experiments

- `PageHeader`
- `FilterBar`
- `DataTable`
- `DeltaPill`
- `ComparisonChart`

### Calibration

- `PageHeader`
- `DataTable`
- `KeyValueList`
- `AuditPanel`
- `PrimaryButton`
- `DangerButton`

## Criterio de aceptación

Un componente entra en el sistema solo si:

- tiene propósito claro
- se reutiliza
- mejora consistencia real
- encaja con el tono editorial-operativo

Si no cumple eso, es mejor no crearlo.
