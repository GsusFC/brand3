# Refactor Noise Policy

## Veredicto

Durante un refactor, el foco es el cambio arquitectonico planificado. Los casos de ruido detectados en batches, scanners o auditorias no deben interrumpir el refactor salvo que bloqueen la seguridad del cambio.

Esta politica existe para evitar que el trabajo derive hacia parches de marca o heuristicas puntuales mientras aun estamos moviendo fronteras estructurales.

## Regla principal

Si aparece ruido durante una prueba de refactor:

1. Se documenta con evidencia.
2. Se clasifica.
3. Se decide si bloquea el refactor.
4. Si no bloquea, se planifica para despues.

No se arregla automaticamente en el momento.

## Clasificacion

### Frontera comun debil

Un caso revela frontera comun debil cuando el ruido atraviesa una decision compartida del sistema, por ejemplo:

- adquisicion de fuentes;
- `StrategicEvidencePacket`;
- `BrandContextBrief`;
- `ResearchPack`;
- `EvidenceGraph`;
- TLDR interpreter;
- readiness/publication gates;
- Scanner API contract.

Decision: registrar como deuda tecnica priorizable y planificar arreglo posterior.

Solo se arregla dentro del refactor activo si el problema invalida el contrato que estamos refactorizando.

### Caso puntual

Un caso es puntual cuando depende de una marca, pagina o patron aislado y no demuestra una frontera comun rota.

Decision: registrar como benchmark/noise case. No convertir en parche inmediato.

### Bloqueante

Un caso es bloqueante cuando:

- rompe tests criticos;
- hace imposible validar el refactor;
- degrada claramente un contrato que estamos cambiando;
- puede publicar datos pobres como validos;
- invalida una decision de rollout.

Decision: arreglar antes de continuar, con test de regresion.

## Informacion minima a registrar

Cada hallazgo de ruido debe capturar:

- fecha;
- run ID o fixture;
- marca y URL;
- bloque afectado;
- texto contaminante;
- frontera atravesada;
- impacto observado;
- clasificacion: frontera comun debil, caso puntual o bloqueante;
- decision: ahora, despues o descartar.

## Criterio de actuacion

El refactor sigue adelante si:

- los tests del contrato en curso pasan;
- el ruido no invalida la frontera que estamos modificando;
- el resultado queda marcado como review/degraded cuando corresponde;
- no hay publicacion automatica de datos pobres como validos.

El refactor se pausa solo si el ruido demuestra que el contrato actual no puede validarse con seguridad.

## Relacion con batches

Los batches son instrumentos de observabilidad, no generadores automaticos de tareas.

Un batch puede descubrir:

- regresiones reales;
- ruido historico que ya existia;
- casos de baja confianza correctamente marcados;
- oportunidades futuras.

No todo hallazgo de batch requiere cambio de codigo inmediato.

## Decision operativa

Hasta terminar el refactor principal:

1. Mantener el foco en fronteras arquitectonicas.
2. Registrar ruido descubierto durante pruebas.
3. No perseguir limpieza total de casos individuales.
4. Resolver solo bloqueantes.
5. Abrir una fase posterior de hardening/noise backlog con evidencias acumuladas.

