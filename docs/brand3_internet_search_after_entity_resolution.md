# Brand3: busqueda en internet despues de resolver la entidad

## Veredicto

Brand3 no busca "informacion general" de una empresa de forma abierta. Primero intenta resolver que entidad esta auditando y despues lanza busquedas con intencion: identidad, superficies propias, contexto externo, competidores, reputacion, novedades y visibilidad AI.

La regla central es que una fuente encontrada en internet no se convierte automaticamente en evidencia. Antes debe clasificarse por relacion con la entidad auditada y por elegibilidad para alimentar un bloque Brand3.

## Flujo corto

```text
brand_name + url
  -> resolver entidad
  -> decidir scope de analisis
  -> generar queries
  -> buscar fuentes externas
  -> clasificar resultados
  -> extraer claims elegibles
  -> enviar solo evidencia limpia al Research Pack / TLDR
```

## 1. Resolver que entidad buscamos

Antes de buscar, Brand3 distingue varios casos:

| Scope | Que significa | Ejemplo |
| --- | --- | --- |
| `company_brand` | La entidad principal parece ser la empresa/marca. | `OpenAI` + `openai.com` |
| `product_with_parent` | La entidad auditada es producto, pero hay una marca matriz relevante. | `ChatGPT` + `chatgpt.com` -> `OpenAI` |
| `ecosystem` | La entidad parece protocolo, ecosistema o red. | `Base` + `base.org` |
| `url_only` | No hay suficiente confianza para resolver una marca completa. | Nombre y dominio no encajan |

Esta decision evita buscar mal. No es lo mismo buscar una marca empresa que un producto dentro de una empresa.

Codigo principal:

- `src/discovery/entity_discovery.py`
- `src/discovery/search_plan.py`

## 2. Construir el plan de busqueda

Despues de resolver la entidad, Brand3 genera un `DiscoverySearchPlan` con:

- `primary_entity`
- `requested_entity`
- `analysis_mode`
- `queries`
- `owned_urls`

### Empresa normal

Para una empresa como `LangChain`, el plan se parece a:

```text
LangChain brand positioning
LangChain latest product updates
LangChain reviews reputation
LangChain competitors
```

### Producto con parent

Para `ChatGPT`, el plan combina producto y matriz:

```text
OpenAI ChatGPT brand positioning
OpenAI ChatGPT product updates
OpenAI ChatGPT reviews
OpenAI ChatGPT competitors
```

Esto es necesario porque la evidencia de producto puede estar en `chatgpt.com`, pero la mision, seguridad, confianza, investigacion o vision pueden estar en `openai.com`.

### Ecosistema o protocolo

Para una entidad como `Base`:

```text
Base ecosystem positioning
Base protocol updates
Base developer community
Base competitors alternatives
```

Aqui importan mas comunidad, docs, developer surfaces y contexto de alternativas.

## 3. Que buscamos exactamente

Las busquedas tienen intenciones concretas.

### Identidad

Objetivo: comprobar si el nombre, dominio y contexto apuntan a la misma entidad.

Buscamos:

- dominio canonico
- parent brand
- producto asociado
- subdominios oficiales
- paginas de producto
- documentacion oficial
- perfiles oficiales o casi oficiales

No buscamos "confirmar a toda costa". Si las senales no encajan, el resultado debe quedar como provisional, dudoso o `url_only`.

### Superficies propias

Objetivo: encontrar paginas owned que puedan sostener bloques Brand3.

Ejemplos:

- home
- about
- mission
- manifesto
- product pages
- pricing
- security
- privacy
- trust
- docs
- customer stories
- testimonials
- case studies

Estas paginas no son equivalentes. Cada una sirve mejor para distintos bloques.

| Superficie | Uso principal |
| --- | --- |
| home / audited surface | magnetism, hero claim, propuesta de valor |
| about / mission / manifesto | mission, vision, core purpose |
| product pages | product offer, audience, outcomes |
| pricing / plans | modelo comercial, packaging |
| security / trust / legal | values, trust, maturity |
| customers / case studies | proof, outcomes |
| docs | producto, developer surface, AI visibility |

### Contexto externo

Objetivo: saber como aparece la marca fuera de su propia web.

Buscamos:

- menciones
- noticias
- articulos
- reviews
- comparativas
- directorios
- comunidades
- paginas de analistas

Estas fuentes pueden aportar reputacion, categoria, prueba externa o contradicciones. Pero no son owned claims.

### Competidores y categoria

Objetivo: entender el espacio competitivo.

Buscamos:

- competidores directos
- alternativas
- comparativas
- listados de categoria
- "similar to X"
- paginas que expliquen el mercado

Este contexto ayuda a interpretar diferenciacion y posicionamiento. No debe confundirse con evidencia interna de la marca.

### AI visibility

Objetivo: detectar presencia en fuentes que sistemas AI o busquedas semanticas pueden usar.

Buscamos:

- docs
- schema
- `llms.txt`
- contenido tecnico
- knowledge graph
- recomendaciones AI
- paginas con informacion estructurada

Esta senal no significa "la marca es fuerte". Significa que hay presencia legible o recuperable en entornos AI/search.

## 4. Proveedores usados para buscar

### Web / Firecrawl

Se usa para scraping de la URL auditada y, cuando aplica, paginas owned adicionales.

Rol:

- capturar contenido propio
- extraer links
- producir markdown para analisis
- alimentar evidencia owned

### Exa

Se usa como motor principal de busqueda semantica externa.

Intents actuales:

- `mentions`
- `competitors`
- `news`
- `ai_visibility`
- `enrichment`

Exa devuelve resultados con URL, titulo, texto, highlights, score, fecha y metadata. Brand3 despues clasifica esos resultados.

### Parallel Shadow

Se usa como busqueda externa opcional para medir cobertura y encontrar candidatos de revision.

Importante: `parallel_shadow` no alimenta scoring ni TLDR. Se guarda como metadata y se muestra como `shadow_sources`.

## 5. Clasificacion de resultados

Despues de buscar, Brand3 clasifica cada resultado.

Campos relevantes:

- `source_class`
- `relation`
- `classification_reason`
- `requires_human_review`

Clases tipicas:

| Clase | Significado |
| --- | --- |
| `owned` | Mismo host o mismo root domain que la marca. |
| `external` | Fuente externa candidata. |
| `marketplace_listing` | Listing externo, requiere cautela. |
| `technical_internal` | Artefacto tecnico como sitemap, robots, schema, etc. |
| `related_unresolved` | Nombre parecido o relacionado, pero dominio distinto. |
| `noise` | Fuente probablemente no util o irrelevante. |

La clasificacion evita que un resultado de busqueda se convierta directamente en conclusion.

## 6. Entity boundary: no mezclar marcas con nombres parecidos

El riesgo mas importante es mezclar entidades.

Ejemplos de problemas:

- una marca con el mismo nombre en otro pais o categoria
- un dominio distinto que contiene el token de la marca
- un marketplace listing ambiguo
- un articulo que menciona una palabra igual pero habla de otra entidad
- una pagina de competidor que aparece en una query de marca

Cuando Brand3 detecta colision de entidad, la fuente puede quedar como:

- `related_unresolved`
- `requires_human_review`
- `noise`
- contexto externo sin soporte para bloques

En el Evidence Graph, una fuente en cuarentena no debe aportar `supports_blocks` al TLDR.

Codigo principal:

- `src/collectors/exa_collector.py`
- `src/research/evidence_graph.py`

## 7. Que convierte una fuente en evidencia util

Una fuente solo deberia alimentar Brand3 si pasa estas preguntas:

```text
1. Pertenece o habla correctamente de la entidad auditada?
2. La relacion con la entidad esta clara?
3. Es owned, externa, competidor, social o ruido?
4. Tiene texto suficiente para extraer un claim?
5. Ese claim puede sostener un bloque Brand3 concreto?
6. Hay alguna colision de entidad o warning que lo invalide?
```

Si falla una pregunta critica, no se elimina necesariamente. Puede quedar como contexto, shadow source, warning o candidato a revision manual.

## 8. Que buscamos por bloque Brand3

La evidencia se orienta a bloques. No toda fuente sirve para todo.

| Bloque | Fuentes preferidas |
| --- | --- |
| `magnetism` | home, audited surface, hero claims, pruebas visibles |
| `value_proposition` | home, product pages, pricing, proof |
| `core_purpose` | about, mission, manifesto |
| `mission` | mission/about, parent home, product system |
| `vision` | mission/about, product roadmap, founder/press si es elegible |
| `values` | values, principles, security, trust, policy |
| `attributes` | tono owned, producto, claims consistentes |
| `personality` | home, about, lenguaje editorial |
| `brand_idea` | home, parent brand, product system, third-party context elegible |

La idea es impedir que, por ejemplo, una review externa invente los valores de la marca o que una pagina de pricing determine la vision.

## 9. Que pasa con resultados ambiguos

Los resultados ambiguos no se borran automaticamente. Se conservan con menor autoridad.

Posibles destinos:

- `shadow_sources`: visible para revision, no decisorio.
- `noise`: fuente registrada pero no usada para TLDR.
- `warnings`: limitacion del run.
- `external_context`: contexto, no claim owned.
- `requires_human_review`: candidato que necesita validacion humana.

Esto permite auditar que se encontro sin contaminar la interpretacion.

## 10. Ejemplo completo

Input:

```text
brand_name = ChatGPT
url = https://chatgpt.com
```

Resolucion:

```text
entity_name = ChatGPT
entity_type = product
analysis_scope = product_with_parent
parent_brand_name = OpenAI
canonical_url = https://chatgpt.com
parent_url = https://openai.com
```

Queries:

```text
OpenAI ChatGPT brand positioning
OpenAI ChatGPT product updates
OpenAI ChatGPT reviews
OpenAI ChatGPT competitors
```

Fuentes que podrian entrar:

- `chatgpt.com`: audited/product surface
- `openai.com`: parent home
- `openai.com/blog/...`: parent/product update
- articulos externos: third-party context o review
- competidores: competitor context

Fuentes que requieren cautela:

- dominios que contengan "chatgpt" pero no sean oficiales
- directorios o marketplaces
- articulos genericos que mencionen ChatGPT junto a otros productos
- paginas SEO con informacion derivada

## 11. Diferencia entre encontrar y usar

Brand3 puede encontrar muchas cosas. Solo algunas deben usarse.

```text
Encontrado en internet
  != fuente relacionada
  != evidencia owned
  != claim valido
  != conclusion Brand3
```

La cadena correcta es:

```text
Resultado encontrado
  -> fuente clasificada
  -> claim extraido
  -> claim elegible
  -> soporte de bloque
  -> interpretacion
```

## 12. Limitaciones actuales

Limitaciones que hay que mantener visibles:

- No existe verificacion legal universal de propiedad de marca.
- La resolucion de entidad combina reglas conocidas y heuristicas.
- Los proveedores externos pueden devolver resultados incompletos o ambiguos.
- Search co-occurrence no prueba relacion.
- Nombre parecido no prueba relacion.
- Marketplace/listing no prueba propiedad.
- Parallel Shadow es observacional hasta que se promueva explicitamente.
- La revision humana sigue siendo necesaria en casos ambiguos.

## 13. Regla operativa

La pregunta correcta despues de buscar no es:

```text
Encontramos informacion sobre esta marca?
```

La pregunta correcta es:

```text
Esta informacion pertenece a la entidad auditada, viene de una fuente clasificada,
tiene suficiente evidencia y puede sostener este bloque Brand3 sin contaminar
la interpretacion?
```

Si la respuesta es no, la informacion debe permanecer como contexto, warning, shadow metadata o noise.

