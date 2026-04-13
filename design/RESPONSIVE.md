# Responsive

## Objetivo

Resolver responsive sin degradar Brand3 a un dashboard comprimido.

La prioridad no es “que quepa todo”. La prioridad es:

- mantener jerarquía
- preservar legibilidad
- no romper el foco en marca
- no convertir tablas complejas en ruido

## Breakpoints

Brand3 trabajará con `4` breakpoints reales:

- `sm`: `640px`
- `md`: `900px`
- `lg`: `1200px`
- `xl`: `1440px`

## Rangos

### `< 640px`

Modo:

- móvil

Reglas:

- layout completamente vertical
- navegación compacta
- tablas complejas pasan a listas estructuradas
- acciones secundarias se colapsan
- metadata técnica se reordena debajo del contenido principal

### `640px - 899px`

Modo:

- móvil grande / tablet pequeña

Reglas:

- una columna dominante
- grids muy controlados
- algunos bloques pueden ir a `2` columnas si no rompen la lectura
- tablas aún simplificadas

### `900px - 1199px`

Modo:

- tablet / small desktop

Reglas:

- experiencia intermedia seria
- se pueden usar `2` columnas
- tablas ya pueden parecer tablas reales, pero con menos columnas visibles
- paneles secundarios se apilan

### `1200px - 1439px`

Modo:

- desktop principal

Reglas:

- experiencia completa
- tablas con todas sus columnas importantes
- hero y paneles respirados

### `1440px+`

Modo:

- desktop amplio

Reglas:

- más aire
- más margen exterior
- no añadir complejidad por tener más espacio
- evitar líneas de texto demasiado largas

## Reglas globales

### Navegación

- `mobile`: top bar compacta + menú colapsado
- `tablet`: top nav simplificada
- `desktop`: top nav completa

### Contenido

- en tamaños pequeños, el contenido editorial manda
- metadata, audit y detalles técnicos bajan de prioridad visual

### Tablas

Las tablas no deben escalar de forma ingenua.

Patrón:

- `mobile`: lista estructurada
- `tablet`: tabla simplificada
- `desktop`: tabla completa

### Acciones

- `mobile`: máximo una acción primaria visible por bloque
- acciones secundarias dentro de menú o fila expandible

### Tipografía

- no reducir tanto que parezca app móvil genérica
- mejor reflujo y stacking que texto microscópico

## Comportamiento por página

### Analyze

#### Mobile

- formulario en una columna
- CTA fijo o muy visible
- jobs recientes debajo

#### Tablet

- formulario ancho
- bloque de jobs recientes aún debajo

#### Desktop

- formulario principal + actividad reciente acompañando

### Jobs

#### Mobile

Usar lista de jobs, no tabla completa.

Cada item debe mostrar:

- logo
- marca
- dominio
- status
- phase
- requested
- duration
- acción primaria

#### Tablet

Tabla simplificada:

- Brand
- Status
- Phase
- Duration
- Action

#### Desktop

Tabla completa:

- Brand
- Status
- Phase
- Requested
- Duration
- Run
- Actions

### Job Detail

#### Mobile

- stack completo
- cabecera compacta
- timeline debajo
- resultado o error en bloque final

#### Desktop

- hero arriba
- timeline y config en dos columnas si hace falta

### Brands

#### Mobile

- lista vertical
- score y trend visibles

#### Tablet

- lista o cards horizontales

#### Desktop

- tabla o lista refinada

### Brand Detail

#### Mobile

Prioridad:

- logo
- nombre
- composite
- dimensiones
- histórico

Reglas:

- hero apilado
- dimensiones en lista o grid 2xN
- insights antes que metadata técnica

#### Tablet

- hero más rico
- gráfico debajo
- runs después

#### Desktop

- hero amplio
- banda de dimensiones
- histórico e insights convivendo

### Runs

#### Mobile

- no tabla completa
- lista de runs con score, brand, profile y fecha

#### Tablet

- tabla reducida

#### Desktop

- tabla completa con fingerprint y acciones

### Run Detail

#### Mobile

- summary arriba
- dimensiones después
- features por bloques colapsables
- audit al final

#### Desktop

- summary y audit pueden convivir arriba
- features con más densidad

### Experiments

#### Mobile

- lista before/after
- delta muy visible

#### Desktop

- tabla clara con before/after y acciones

### Calibration

#### Mobile

- navegación interna por tabs simples
- listas y formularios apilados

#### Desktop

- vista más técnica y densa

## Patrones de transformación

### Tabla a lista estructurada

Cuando una tabla no cabe bien:

- convertir cada fila en bloque vertical
- mantener la marca arriba
- agrupar metadata secundaria debajo
- dejar una sola acción visible

### Dos columnas a una

En móvil:

- panel principal arriba
- panel secundario debajo

Nunca:

- dos columnas estrechas compitiendo por atención

### Hero complejo a hero apilado

En pantallas pequeñas:

- nombre y score arriba
- profile/niche debajo
- metadata técnica al final

## Prioridades por viewport

### Siempre visibles

- marca
- estado principal
- score principal
- CTA principal

### Reordenables

- fingerprint
- gate config
- audit metadata
- actions secundarias

### Ocultables o colapsables

- detalles extensos
- raw artifacts
- metadata poco crítica

## Regla final

Responsive en Brand3 no consiste en hacer todo más pequeño.

Consiste en decidir qué información lidera en cada tamaño de pantalla y cómo preservar la lectura de marca sin perder capacidad operativa.
