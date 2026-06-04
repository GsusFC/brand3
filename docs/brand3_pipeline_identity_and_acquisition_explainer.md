# Brand3 Pipeline: identidad, adquisicion y evidencia

## Veredicto

Brand3 no trata una URL como "la marca". La URL es una semilla. El pipeline intenta resolver que entidad se esta auditando, separa superficies propias de contexto externo, recoge evidencia desde varias fuentes y despues filtra esa evidencia antes de permitir que alimente scoring, Research Pack o TLDR.

La garantia real no es "sabemos con certeza absoluta que esta marca es X". La garantia actual es mas limitada y mas correcta: Brand3 produce una entidad operativa con confianza, evidencias y warnings; cuando hay ambiguedad, el sistema debe conservar esa ambiguedad y evitar promocionar evidencia dudosa.

## Resumen ejecutivo

El flujo puede leerse asi:

```text
brand_name + url
  -> entity discovery
  -> discovery search plan
  -> raw input collection
  -> entity research packet
  -> evidence graph
  -> brand research pack
  -> Brand3 / Magnetism interpretation
```

La primera mitad del pipeline responde a dos preguntas:

1. Que entidad estamos analizando realmente.
2. Que informacion se puede usar sin mezclar ruido, terceros o marcas con nombres parecidos.

## 1. Entrada: una URL no equivale a una marca

El usuario aporta normalmente:

- `brand_name`
- `url`

El sistema normaliza ambos. La URL sirve para derivar dominio, host y root domain. El nombre sirve para matching textual. Ninguna de estas senales es suficiente por si sola para confirmar identidad.

Ejemplos:

- `OpenAI` + `https://openai.com` es una marca empresa razonable.
- `ChatGPT` + `https://chatgpt.com` es un producto con parent brand `OpenAI`.
- `Claude` + `https://claude.ai` es un producto con parent brand `Anthropic`.
- `Obscure Thing` + `https://example.com` no debe resolverse agresivamente como marca real si nombre y dominio no encajan.

Codigo principal:

- `src/discovery/entity_discovery.py`
- `tests/test_entity_discovery.py`

## 2. Entity discovery: resolucion determinista de identidad

La primera decision formal ocurre en `discover_entity()`.

Este modulo es deliberadamente determinista y no hace red. Devuelve un `EntityDiscoveryResult` con:

- `entity_name`
- `entity_type`
- `analysis_scope`
- `canonical_brand_name`
- `canonical_url`
- `parent_brand_name`
- `parent_url`
- `product_name`
- `confidence`
- `evidence`
- `warnings`

Los modos principales son:

| Modo | Significado |
| --- | --- |
| `company_brand` | La entidad auditada parece ser la marca empresa. |
| `product_with_parent` | La entidad auditada parece ser un producto con marca matriz. |
| `ecosystem` | La entidad parece protocolo/ecosistema, no empresa convencional. |
| `url_only` | No hay suficiente relacion entre nombre y dominio; se limita el alcance. |

Regla importante: si el nombre y el dominio no encajan, el sistema baja confianza y emite warnings como `brand_domain_match_failed`. Eso es preferible a inventar una identidad.

## 3. Search plan: convertir identidad en estrategia de busqueda

Despues de resolver la entidad operativa, `build_discovery_search_plan()` convierte esa resolucion en:

- `primary_entity`
- `requested_entity`
- `analysis_mode`
- `queries`
- `owned_urls`

Esto evita busquedas pobres o ambiguas.

Ejemplo para `ChatGPT`:

```text
primary_entity: OpenAI
requested_entity: ChatGPT
analysis_mode: product_with_parent
queries:
  - OpenAI ChatGPT brand positioning
  - OpenAI ChatGPT product updates
  - OpenAI ChatGPT reviews
  - OpenAI ChatGPT competitors
owned_urls:
  - https://openai.com
  - https://chatgpt.com
```

Codigo principal:

- `src/discovery/search_plan.py`

## 4. Adquisicion: que se recoge ademas del scraping web

La recogida de inputs se orquesta en `collect_raw_inputs()`.

Fuentes actuales:

| Fuente | Rol |
| --- | --- |
| `context` | Senales tecnicas y estructurales del sitio: cobertura, contexto, artefactos como sitemap/metadata cuando apliquen. |
| `web` | Scraping de la URL auditada y paginas owned enriquecidas. |
| `exa` | Busqueda externa: menciones, news, competidores y visibilidad AI. |
| `parallel_shadow` | Busqueda externa opcional para cobertura y revision manual. No alimenta scoring ni TLDR. |
| `social` | Datos sociales opcionales. |
| `competitors` | Contexto competitivo opcional usando Exa y web. |

Codigo principal:

- `src/services/input_collection.py`
- `src/collectors/web_collector.py`
- `src/collectors/context_collector.py`
- `src/collectors/exa_collector.py`
- `src/collectors/parallel_shadow_collector.py`
- `src/collectors/competitor_collector.py`
- `src/collectors/social_collector.py`

## 5. Exa: contexto externo con clasificacion de fuente

Exa se usa para obtener informacion que no depende solo de la web propia:

- menciones de marca
- reputacion/reviews
- noticias
- competidores
- visibilidad en contenido relacionado con AI

El collector no deberia tratar todos los resultados como verdad. Clasifica cada resultado con campos como:

- `source_class`
- `relation`
- `classification_reason`
- `requires_human_review`

Casos relevantes:

- mismo host o mismo root domain: posible owned surface
- marketplace/listing: requiere revision
- ruido tecnico o fuentes irrelevantes: no se debe promocionar sin control
- mismo nombre en root domain distinto: `related_unresolved`, requiere revision

Codigo principal:

- `src/collectors/exa_collector.py`

## 6. Parallel Shadow: cobertura observacional, no decision automatica

`ParallelShadowCollector` consulta Parallel Search para intents como:

- `mentions`
- `competitors`
- `news`
- `ai_visibility`

Pero su contrato es explicito: es observacional.

No debe alimentar:

- scoring
- TLDR
- production decisions

Su salida se guarda como raw input y se expone despues como `shadow_sources` en Research Pack/API para revision humana y diagnostico de cobertura.

Codigo principal:

- `src/collectors/parallel_shadow_collector.py`
- `tests/test_brand_research_pack_builder.py`
- `web/templates/scanner_api.html.j2`

## 7. Entity Research Packet: mapa de superficies propias y scope

El `EntityResearchPacket` separa:

- URL auditada
- parent brand
- producto
- superficies owned candidatas
- roles de pagina
- guidance por bloque Brand3

Roles tipicos:

- `audited_surface`
- `parent_home`
- `mission_about`
- `product_system`
- `policy_security`
- `pricing`
- `blog_feed`
- `proof_customer`

Esto importa porque no todas las paginas sirven para todo. Por ejemplo:

- `values` deberia apoyarse mas en `policy_security` o `mission_about`.
- `value_proposition` puede apoyarse en `audited_surface` o `product_system`.
- `magnetism` se apoya especialmente en la superficie auditada.

Codigo principal:

- `src/reports/entity_research_packet.py`

## 8. Discovery enrichment: paginas owned y busquedas adicionales

`build_discovery_enrichment()` puede ampliar la evidencia con:

- owned URLs del search plan
- owned surfaces del Entity Research Packet
- queries de enriquecimiento cuando el preview de evidencia lo recomienda

La salida conserva diagnosticos:

- `applied`
- `urls_used`
- `queries_used`
- `added_owned_evidence`
- `added_third_party_evidence`
- `entity_research_urls_used`

Esto permite enriquecer sin mezclar de forma silenciosa de donde vino cada senal.

Codigo principal:

- `src/discovery/enrichment.py`
- `tests/test_discovery_enrichment.py`

## 9. Evidence Graph: frontera entre evidencia util y ruido

El Evidence Graph convierte el snapshot persistido de Brand Audit en una estructura trazable:

- `ResearchSource`
- `EvidenceClaim`
- `BrandResearchRun`
- `EvidenceGraph`

Cada fuente queda tipada:

- `owned_home`
- `owned_about`
- `owned_product`
- `owned_pricing`
- `owned_security`
- `owned_docs`
- `owned_proof`
- `press_founder`
- `third_party_review`
- `third_party_context`
- `social`
- `competitor_context`
- `noise`
- `unknown`

Cada claim queda tipado:

- `hero_claim`
- `product_offer`
- `audience`
- `outcome`
- `mission`
- `vision`
- `values`
- `personality`
- `proof`
- `founder_press`
- `feature_evidence`
- `noise`
- `unknown`

La parte critica es el entity boundary gate: si una fuente externa parece colisionar con una entidad de nombre parecido, se marca como `noise` y se le quitan `supports_blocks`. En otras palabras: puede aparecer como dato revisable, pero no debe alimentar el TLDR.

Codigo principal:

- `src/research/evidence_graph.py`
- `tests/test_research_evidence_graph.py`

## 10. Research Pack y Magnetism

El Magnetism Scanner no deberia recolectar informacion por su cuenta cuando analiza una URL. El flujo canonico es:

```text
URL
  -> Brand Audit run persistido
  -> snapshot de Brand Audit
  -> Evidence Graph
  -> Brand Research Pack
  -> Magnetism Extractor / Analyst TLDR
```

Esto mantiene una unica base de evidencia para Brand Audit y Magnetism.

Codigo principal:

- `src/services/magnetism_service.py`
- `src/features/magnetism/extractor.py`
- `src/reports/brand_research_pack.py`

## 11. Persistencia y reproducibilidad

Los inputs se guardan como `raw_inputs` asociados a un run. El snapshot se recupera con `SQLiteStore.get_run_snapshot()`.

Esto permite:

- renderizar resultados historicos sin regenerarlos
- exponer API sobre scans ya persistidos
- auditar que fuentes alimentaron un resultado
- distinguir cache hit, miss, partial, skipped o disabled

Codigo principal:

- `src/storage/sqlite_store.py`
- `src/services/input_collection.py`

## 12. Que protege el sistema

Protecciones existentes:

- No aceptar nombre + URL como identidad verificada si no encajan.
- Separar company brand, product brand, parent brand y ecosystem.
- Construir queries segun el scope de entidad.
- Clasificar Exa results por relacion con la marca.
- Marcar same-name different-root como unresolved/review.
- Mantener Parallel Shadow como metadata, no como input decisorio.
- Convertir fuentes dudosas en `noise`.
- Quitar soporte de bloques Brand3 a claims en cuarentena.
- Persistir raw inputs para auditoria.

## 13. Que no protege todavia

Limitaciones actuales:

- No hay verificacion universal de propiedad legal de una marca.
- El entity discovery contiene reglas conocidas y heuristicas; no es un grafo global de marcas.
- Exa y Parallel pueden devolver resultados buenos, incompletos o ambiguos.
- Una fuente third-party puede ser util, pero no debe ser tratada como owned.
- Las superficies relacionadas no deben inferirse solo por similitud de nombre.
- La revision humana sigue siendo necesaria para casos de dominios ambiguos, productos con parent poco claro, marketplaces y marcas homonimas.

## 14. Regla mental para evaluar el pipeline

La pregunta correcta no es:

```text
Ha encontrado informacion sobre esta palabra?
```

La pregunta correcta es:

```text
Esa informacion pertenece a la entidad auditada, tiene una fuente trazable,
esta clasificada con el scope correcto y puede alimentar este bloque Brand3?
```

Si la respuesta no es demostrable, la informacion debe quedar como contexto, shadow metadata, warning o noise; no como conclusion.

