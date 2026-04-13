# Brand3 Scoring Engine

Brand health scoring system. Measures how well a brand works as a system.

**Input:** URL
**Output:** Score 0-100 + breakdown por dimensión

## 5 Dimensiones

1. **Coherencia** — ¿el messaging, visual y tono son consistentes across touchpoints?
2. **Presencia** — ¿dónde aparece y con qué volumen? (web, social, AI visibility)
3. **Percepción** — ¿qué sentiment genera? ¿Cómo hablan de ella?
4. **Diferenciación** — ¿dice algo distinto a sus competidores o es genérica?
5. **Vitalidad** — ¿está activa, publicando, evolucionando, o es una marca muerta?

## Pipeline

```
URL entrada → Recolección → Extracción de features → Scoring → Normalización → Output
```

## Regla fundamental

Sin inputs manuales del usuario. Metes la URL, el algoritmo hace el resto.

## Stack

- Python 3.9+
- Firecrawl (web scraping via CLI)
- Exa (semantic search + AI visibility)
- Social media profile scraping

## Collectores

1. **WebCollector** — Scrapes the brand website using Firecrawl
2. **ExaCollector** — Semantic search and AI visibility via Exa API
3. **SocialCollector** — Scrapes public social media profiles (Instagram, LinkedIn, TikTok, Twitter/X)

## Uso

```bash
# Análisis completo
python3 main.py https://stripe.com Stripe

# Sin LLM (más rápido)
python3 main.py https://stripe.com Stripe --no-llm

# Sin scraping de social media
python3 main.py https://stripe.com Stripe --no-social
```

## Benchmarks

- Exploratory benchmark actual: [examples/startup_benchmark.json](/Users/gsus/brand3-scoring/examples/startup_benchmark.json)
- Template para benchmark canónico: [examples/canonical_benchmark.template.json](/Users/gsus/brand3-scoring/examples/canonical_benchmark.template.json)
- Política de benchmark: [docs/benchmark_policy.md](/Users/gsus/brand3-scoring/docs/benchmark_policy.md)

## InsForge

- Plan v1 para webapp multiusuario: [docs/insforge_v1.md](/Users/gsus/brand3-scoring/docs/insforge_v1.md)
- Esquema SQL inicial para InsForge: [db/insforge_v1.sql](/Users/gsus/brand3-scoring/db/insforge_v1.sql)
- Handoff para retomar el proyecto: [docs/HANDOFF.md](/Users/gsus/brand3-scoring/docs/HANDOFF.md)

## Design

- Índice de diseño/frontend: [design/README.md](/Users/gsus/brand3-scoring/design/README.md)
- Documento maestro de diseño: [design/DESIGN.md](/Users/gsus/brand3-scoring/design/DESIGN.md)
- Plan de frontend: [design/FRONTEND_PLAN.md](/Users/gsus/brand3-scoring/design/FRONTEND_PLAN.md)
- Responsive y breakpoints: [design/RESPONSIVE.md](/Users/gsus/brand3-scoring/design/RESPONSIVE.md)
- Sistema de componentes: [design/COMPONENTS.md](/Users/gsus/brand3-scoring/design/COMPONENTS.md)
- Tokens base: [design/TOKENS.css](/Users/gsus/brand3-scoring/design/TOKENS.css)

## Fases

- **Fase 1**: Uso interno FLOC*. Validación con clientes reales.
- **Fase 2**: Self-serve freemium.
- **Fase 3**: Data como producto para VCs.
