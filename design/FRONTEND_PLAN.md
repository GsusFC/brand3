# Frontend Plan

## Objetivo

Construir una webapp accesible para equipo y terceros, usando el backend actual como primera fuente de datos y dejando preparada la migración progresiva a InsForge.

## Principios

- no bloquear frontend por la migración completa a InsForge
- no diseñar una app distinta a la que luego se implementará
- priorizar páginas que validan producto, no solo infraestructura

## Stack recomendado

- `Next.js`
- `TypeScript`
- `App Router`
- `React Server Components` donde encaje
- fetch simple hacia la API existente

## Fase 1

Objetivo: app usable de lectura y operación básica.

Páginas:

- `Analyze`
- `Jobs`
- `Job Detail`
- `Brands`
- `Brand Detail`
- `Run Detail`

Dependencias backend ya resueltas:

- jobs
- runs
- brands
- brand report

## Fase 2

Objetivo: comparaciones y calibración.

Páginas:

- `Experiments`
- `Compare Runs`
- `Calibration`

Dependencias backend:

- experiments
- gate config
- baselines
- compare/promote/rollback

## Fase 3

Objetivo: experiencia multiusuario real sobre InsForge.

Trabajo:

- auth
- workspaces
- datos persistidos en InsForge
- realtime para jobs

## Estructura recomendada

```text
frontend/
  app/
  components/
  lib/
  styles/
  public/
```

La definición funcional de `components/` debe seguir [`COMPONENTS.md`](/Users/gsus/brand3-scoring/design/COMPONENTS.md).

## Capas

### `app/`

Rutas y composición de página.

### `components/`

Componentes reutilizables:

- brand
- jobs
- runs
- charts
- layout
- calibration

### `lib/`

- cliente API
- tipos
- helpers de formato
- polling simple

### `styles/`

- tokens
- globals
- tablas
- utilidades de layout

## Rutas sugeridas

- `/`
- `/analyze`
- `/jobs`
- `/jobs/[id]`
- `/brands`
- `/brands/[brand]`
- `/runs/[id]`
- `/experiments`
- `/calibration`

## Datos por página

### `/analyze`

- `POST /api/analyze/jobs`
- `GET /api/analyze/jobs?limit=...`

### `/jobs`

- `GET /api/analyze/jobs`

### `/jobs/[id]`

- `GET /api/analyze/jobs/{id}`

### `/brands`

- `GET /api/brands`

### `/brands/[brand]`

- `GET /api/brands/{brand_name}/report`

### `/runs/[id]`

- `GET /api/runs/{run_id}`

### `/experiments`

- `GET /api/experiments`

### `/calibration`

- `GET /api/gate-config`
- `GET /api/baselines`

## Estados críticos

Toda página debe contemplar:

- loading
- empty
- error
- no data yet
- stale or partial data

## Riesgos

- convertir jobs en una tabla genérica y perder foco en marca
- caer en una estética estándar de dashboard
- meter demasiadas cards donde una buena tabla es mejor

## Criterio de acabado para v1

V1 está lista cuando:

- se puede lanzar un análisis
- se puede seguir el job
- se puede abrir la marca
- se puede entender una run
- la app ya transmite identidad propia
