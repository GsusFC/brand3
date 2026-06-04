# Brief de graficos: Exa como baseline del Search Enrichment Lab

Fuente de datos interna: `out/search_enrichment_lab/20260604T084043Z/summary.json`  
CSV: `docs/comms/brand3_exa_selection_chart_data.csv`  
JSON: `docs/comms/brand3_exa_selection_chart_data.json`

## Mensaje principal

Exa no gana por volumen bruto. Gana porque en esta pasada del Lab entrega mas evidencia util, menos ruido, menos revision humana y menor latencia.

## Graficos recomendados

### 1. Score experimental por proveedor

Tipo: barras horizontales.  
Metrica: `provider_score`.  
Lectura: Exa 70.01 frente a Tavily 31.50.

Caption sugerido:

> Exa funciona mejor como baseline del Lab: mas evidencia util con menos penalizaciones operativas.

### 2. Fuentes elegibles vs no elegibles

Tipo: barras apiladas por proveedor.  
Metricas: `eligible_sources`, `ineligible_sources`.  
Lectura: Exa 24 elegibles y 6 no elegibles; Tavily 19 elegibles y 11 no elegibles.

Caption sugerido:

> La diferencia no esta en encontrar enlaces, sino en cuantos pueden entrar al pipeline sin contaminar identidad.

### 3. Riesgo operativo

Tipo: barras agrupadas.  
Metricas: `human_review_count`, `noise_hits`, `marketplace_hits`, `related_unresolved_hits`.  
Lectura: Tavily genera mas revision humana y ruido; Exa genera mas entidades relacionadas no resueltas, pero sin ruido clasificado.

Caption sugerido:

> El proveedor base debe reducir trabajo manual y ambiguedad, no ampliarlos.

### 4. Latencia media

Tipo: barras simples.  
Metrica: `average_latency_ms`.  
Lectura: Exa 989.9 ms; Tavily 4099.3 ms.

Caption sugerido:

> La latencia importa cuando el analisis requiere varias consultas por entidad.

### 5. Composicion de fuente

Tipo: barras apiladas por clase.  
Metricas: `external_hits`, `owned_hits`, `noise_hits`, `marketplace_hits`, `related_unresolved_hits`.  
Lectura: Exa tiene mas owned y menos ruido; Tavily trae algo mas de externo bruto, pero tambien ruido y marketplace.

Caption sugerido:

> Para identidad, una fuente owned bien clasificada puede valer mas que varios resultados externos ambiguos.

## Notas de diseno

- Evitar una estetica de "benchmark definitivo".
- Usar lenguaje de Lab: provisional, muestra controlada, score experimental.
- Incluir siempre el tamano de muestra: 5 casos, 30 observaciones por proveedor.
- No usar porcentajes sin mostrar tambien el denominador.
- No presentar Tavily como descartado globalmente; presentarlo como complemento potencial.

## Numeros clave

| Metrica | Exa | Tavily |
| --- | ---: | ---: |
| Score experimental | 70.0101 | 31.5 |
| Fuentes elegibles | 24 | 19 |
| Fuentes no elegibles | 6 | 11 |
| Revision humana | 2 | 5 |
| Ruido | 0 | 4 |
| Owned | 8 | 4 |
| Consenso | 2 | 2 |
| Latencia media | 989.9 ms | 4099.3 ms |

