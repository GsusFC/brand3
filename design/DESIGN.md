# Brand3 Design

## 1. North Star

Brand3 no es un panel de métricas. Es una mesa de análisis de marcas.

La interfaz debe ayudar a:

- lanzar análisis
- entender resultados
- comparar runs
- revisar calibraciones
- operar el sistema sin perder contexto de marca

La unidad mental principal es la marca. No el job. No el run. No el ID.

## 2. Producto Visual

Dirección recomendada:

- `editorial tech analysis desk`

La app debe mezclar:

- sensibilidad editorial
- rigor operativo
- densidad informativa controlada

Debe transmitir:

- criterio
- calma
- claridad
- gusto

Debe evitar:

- dashboard SaaS genérico
- estética AI brillante
- plantillas morado sobre blanco
- exceso de cards y gráficas sin jerarquía

## 3. Principios

### Brand-first

Cada pantalla debe priorizar:

- logo
- nombre
- dominio
- estado de la marca

### Dense but calm

Hay bastante información, pero bien respirada.

### Analytical, not corporate

La app debe parecer una herramienta de análisis, no un CRM ni un backoffice.

### Explainable

Toda nota tiene que poder seguirse:

- score
- dimensiones
- features
- audit
- profile/niche

### System-aware

El producto debe distinguir entre:

- estado de la marca
- estado del análisis
- estado del scoring system

## 4. Paleta

### Base

- `--bg`: `#f3efe7`
- `--surface`: `#fbf8f2`
- `--surface-2`: `#efe8dc`
- `--surface-3`: `#e6dece`
- `--border`: `#d9cfbf`
- `--text`: `#181716`
- `--text-muted`: `#5f5a52`

### Accent

Accent principal recomendado:

- `--accent`: `#a64b2a`
- `--accent-soft`: `#e8c1b2`

Secundarios:

- `--ink-blue`: `#27445d`
- `--olive`: `#5e6b47`

### Semánticos

- `--success`: `#40634a`
- `--warning`: `#9a6a18`
- `--danger`: `#9b3a30`
- `--info`: `#355c7d`

## 5. Tipografía

Combinación recomendada:

- headings: `Fraunces`
- body/ui/tables: `Manrope`

Alternativas válidas:

- serif: `Cormorant Garamond`
- sans: `Public Sans`, `Instrument Sans`

Regla:

- títulos y momentos editoriales con serif
- UI, números, tablas y controles con sans

## 6. Escala tipográfica

- `display`: `48/52`
- `h1`: `40/44`
- `h2`: `32/36`
- `h3`: `22/28`
- `section-label`: `12/14`
- `body`: `15/22`
- `table`: `14/20`
- `meta`: `12/16`

## 7. Layout

### Grid

- `max-width`: `1440px`
- grid de `12 columnas`
- gutters generosos

### Spacing

Sistema base:

- `4`
- `8`
- `12`
- `16`
- `24`
- `32`
- `48`
- `64`

### Superficies

- usar bordes finos
- sombras mínimas
- separación por aire y contraste suave

## 8. Navegación

Primera versión recomendada:

- top nav principal
- navegación local por página

Secciones:

- `Analyze`
- `Jobs`
- `Brands`
- `Runs`
- `Experiments`
- `Calibration`

No empezar con sidebar pesada si no hace falta.

## 9. Arquitectura de páginas

### Analyze

Objetivo:

- lanzar análisis nuevos
- mostrar actividad reciente

Contenido:

- H1 editorial
- formulario central
- toggles `use_llm` y `use_social`
- jobs recientes
- marcas recientes

### Jobs

Objetivo:

- operar el pipeline
- entender estado de ejecución

Tabla principal:

- Brand
- Status
- Phase
- Requested
- Duration
- Run
- Actions

La columna `Brand` debe incluir:

- logo
- nombre
- dominio

### Job Detail

Objetivo:

- seguir un análisis concreto

Contenido:

- cabecera con marca, estado y fase
- timeline de eventos
- configuración usada
- resultado o error

### Brands

Objetivo:

- explorar el universo de marcas analizadas

Contenido:

- lista o tabla de marcas
- latest composite
- average composite
- trend
- latest profile/fingerprint

### Brand Detail

Página central del producto.

Contenido:

- hero con logo, nombre, dominio
- composite principal
- dimensiones
- histórico
- insights
- runs recientes

Debe sentirse como un informe vivo.

### Runs

Objetivo:

- auditoría transversal
- debugging

Tabla:

- Run ID
- Brand
- Composite
- Timestamp
- Profile
- Fingerprint

### Run Detail

Objetivo:

- explicar la nota

Contenido:

- composite
- profile
- niche/subtype
- dimensiones
- features
- audit
- artifacts si existen

### Compare Runs

Objetivo:

- comparar before/after o runs distintas

Contenido:

- summary con delta
- diferencias por dimensión
- fingerprint/profile/baseline

### Experiments

Objetivo:

- revisar calibraciones

Contenido:

- tabla de experimentos
- before/after
- delta
- fingerprint before/after
- actions

### Calibration

Objetivo:

- operar el sistema de scoring

Subsecciones:

- Candidates
- Versions
- Baselines
- Gate Config

## 10. Sistema de componentes

Ver inventario detallado en [`COMPONENTS.md`](/Users/gsus/brand3-scoring/design/COMPONENTS.md).

### Brand Row

Debe ser el patrón base de identidad.

Incluye:

- logo
- nombre
- dominio
- metadata opcional

### Score Chip

No usar gauges circulares.

Debe incluir:

- número grande
- contexto textual
- opcionalmente delta o barra sutil

### Status Pill

Pequeña y contenida.

Estados mínimos:

- `queued`
- `running`
- `done`
- `failed`
- `cancelled`

### Phase Pill

Separada de `status`.

Fases:

- `collecting`
- `extracting`
- `scoring`
- `finalizing`

### Insight Block

Bloque corto de lectura humana.

Uso:

- resumen de run
- explicación de score
- evidencia editorial

### Delta Table

Tabla para comparaciones:

- before
- after
- delta

### Audit Panel

Bloque técnico que muestra:

- profile
- niche
- subtype
- baseline
- gate config
- fingerprint

### Empty State

Necesario en:

- brands
- jobs
- runs
- experiments

Debe ser sobrio y útil, no ilustrado.

## 11. Tablas

Las tablas son un asset central del producto.

Reglas:

- filas cómodas
- alineación impecable
- hover sutil
- separadores finos
- poca decoración

La tabla de jobs y la tabla de runs deben diseñarse casi como componentes premium.

## 12. Gráficos

Usarlos con moderación.

Solo para:

- histórico de composite
- histórico por dimensión
- comparación before/after

Reglas:

- líneas finas
- grid casi invisible
- pocos colores
- sin espectáculo

## 13. Motion

Muy poca.

Permitido:

- fade corto
- slide corto
- stagger leve

No:

- microanimaciones constantes
- loaders espectaculares
- motion ornamental

## 14. Iconografía

Mínima.

Usar solo cuando reduzca fricción.

No cargar la UI con iconos donde el texto ya es claro.

## 15. Tono de copy

La app debe hablar como analista, no como copiloto AI.

Bueno:

- `Run analysis`
- `Latest scoring state`
- `Signals were too weak to assign a specialist profile`
- `This run used the active enterprise_ai calibration`

Malo:

- `Unlock insights`
- `Your AI copilot is thinking`
- `Boost your brand intelligence`

## 16. Estados de datos

Cada pantalla debe contemplar:

- `loading`
- `empty`
- `error`
- `partial data`
- `stale data`

Especialmente importante en:

- jobs
- run detail
- brand detail

## 17. Responsive

Ver detalle completo en [`RESPONSIVE.md`](/Users/gsus/brand3-scoring/design/RESPONSIVE.md).

### Desktop

Modo principal. Aquí vive la experiencia completa.

### Tablet

- conservar jerarquía
- apilar paneles secundarios

### Mobile

- priorizar lectura vertical
- evitar tablas horizontales interminables
- convertir algunas tablas en listas estructuradas

## 18. Mapeo a API actual

Endpoints ya disponibles:

- `GET /health`
- `POST /api/analyze`
- `POST /api/analyze/jobs`
- `POST /api/analyze/jobs/{job_id}/retry`
- `POST /api/analyze/jobs/{job_id}/cancel`
- `GET /api/analyze/jobs`
- `GET /api/analyze/jobs/{job_id}`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/brands`
- `GET /api/brands/{brand_name}/report`
- `GET /api/profiles`
- `GET /api/experiments`
- `GET /api/gate-config`
- `POST /api/gate-config`
- `GET /api/baselines`
- `GET /api/versions/{version_id}/compare`
- `POST /api/versions/{version_id}/promote`
- `POST /api/versions/{version_id}/rollback`

Esto permite diseñar ya la webapp v1 sin esperar a toda la migración a InsForge.

## 19. Recomendación técnica frontend

Para webapp pública y mantenible:

- `Next.js`
- `TypeScript`
- `App Router`
- CSS variables + utilidades

No hace falta decidir la librería de componentes todavía.

Regla más importante:

el diseño no debe depender de una UI kit genérica.

## 20. Prioridad de implementación

Orden recomendado:

1. `Analyze`
2. `Jobs`
3. `Job Detail`
4. `Brand Detail`
5. `Run Detail`
6. `Experiments`
7. `Calibration`

## 21. Criterio final

Si hay que elegir entre:

- más widgets
- o más claridad

siempre elegir claridad.

Si hay que elegir entre:

- más color
- o más jerarquía tipográfica

siempre elegir jerarquía tipográfica.

Si hay que elegir entre:

- más “dashboard”
- o más “informe operativo”

siempre elegir informe operativo.
