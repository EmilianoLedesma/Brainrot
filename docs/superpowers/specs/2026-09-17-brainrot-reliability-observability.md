# Diseño: Brainrot --- Reliability, Observability & Extensible Pipeline Architecture

**Fecha:** 2026-09-17\
**Estado:** Diseño técnico completo, pendiente de plan de implementación
(`superpowers:writing-plans`)\
**Precede a:** un plan TDD siguiendo el patrón de
`superpowers:writing-plans`

## 1. Contexto y alcance

Brainrot ya implementa una fábrica automatizada de contenido corto con
pipelines de generación, repurpose, Reddit, renderizado, scheduling y
publicación. El sistema actual es funcional, pero la siguiente etapa no
debe consistir en agregar otro pipeline: debe convertir la
infraestructura existente en una plataforma más confiable, observable,
idempotente y extensible.

El objetivo de este diseño es reforzar el sistema alrededor de cinco
capacidades:

1.  ciclo de vida confiable de jobs;
2.  ejecución idempotente y recuperable;
3.  observabilidad operacional;
4.  arquitectura extensible de pipelines;
5.  retroalimentación de rendimiento para scheduling adaptativo.

Este diseño mantiene las capacidades actuales y evita introducir
Redis/RabbitMQ, múltiples workers o nuevos pipelines como parte de este
incremento.

## 2. Estado actual relevante

El sistema contiene:

-   FastAPI como API;
-   React + Vite como dashboard;
-   Supabase/PostgreSQL como persistencia;
-   Supabase Storage para medios remotos;
-   workers persistentes;
-   pipelines H1 Repurpose, H2 Brainrot y H2b Reddit Narrator;
-   FFmpeg, Edge-TTS, faster-whisper y Claude;
-   scheduler basado en jobs persistentes;
-   publicación hacia YouTube, TikTok e Instagram;
-   tests de pipeline y base de datos.

Los workers son actualmente el principal punto de concentración de
ejecución. El modelo actual debe evolucionar sin romper las interfaces
de los pipelines existentes.

## 3. Problema que resuelve este diseño

El sistema puede producir contenido, pero necesita garantías explícitas
para operar durante ejecuciones largas y ante fallos parciales.

Los principales riesgos a resolver son:

-   jobs atascados en ejecución;
-   reintentos que produzcan efectos duplicados;
-   publicaciones duplicadas;
-   ausencia de trazabilidad por etapa;
-   recuperación manual de trabajos abandonados;
-   poca visibilidad de duración, errores y throughput;
-   dificultad para incorporar nuevos pipelines sin modificar el worker
    central;
-   scheduler sin suficiente información operacional para adaptar la
    cadencia.

## 4. Objetivos

### 4.1 Objetivos funcionales

-   Representar explícitamente el ciclo de vida de un job.
-   Reclamar jobs de forma segura mediante locking/lease.
-   Reintentar fallos transitorios con backoff.
-   Recuperar jobs abandonados.
-   Evitar duplicación mediante idempotency keys.
-   Registrar la ejecución de cada etapa relevante.
-   Exponer métricas operacionales.
-   Mostrar estado y ejecución de pipelines en el dashboard.
-   Registrar resultados de publicación.
-   Permitir que el scheduler use métricas de rendimiento disponibles.
-   Definir una interfaz estable para pipelines futuros.

### 4.2 Objetivos no funcionales

-   Mantener workers stateless.
-   Mantener Supabase como fuente de verdad.
-   Mantener Storage remoto como persistencia de medios.
-   No introducir una cola externa en esta fase.
-   Mantener compatibilidad con H1, H2 y H2b.
-   Mantener el API key del lado servidor para operaciones
    privilegiadas.
-   Evitar cambios destructivos de esquema.
-   Mantener el diseño compatible con una futura migración a
    Redis/RabbitMQ.

## 5. Fuera de alcance

No se construye en esta fase:

1.  Redis/RabbitMQ.
2.  Horizontal scaling real.
3.  Nuevos pipelines de contenido.
4.  OAuth onboarding completo de plataformas.
5.  A/B testing.
6.  Generación de thumbnails.
7.  Multi-language pipelines.
8.  Sistema avanzado de ML para optimización de contenido.

Estos elementos pueden consumir las interfaces definidas por este diseño
posteriormente.

## 6. Modelo de ciclo de vida de jobs

El job debe tener estados explícitos y transiciones controladas.

``` text
pending
  ↓
processing
  ├──→ completed
  ├──→ retry_wait
  └──→ failed

processing
  └──→ pending  (recovery de lease abandonado)

retry_wait
  └──→ processing
```

`failed` representa un job que agotó sus reintentos o falló de forma no
recuperable.

El worker nunca debe considerar un job exitoso solamente porque una
función terminó sin excepción: la transición persistida a `completed`
debe ser parte de la operación.

## 7. Locking y recuperación

La reclamación de un job debe ser atómica.

Cada ejecución debe poder identificar:

-   worker que posee el lease;
-   momento de inicio;
-   momento de expiración del lease;
-   número de intento;
-   timestamps de inicio/finalización;
-   error estructurado cuando corresponda.

Si un worker muere, otro worker podrá recuperar el job una vez expirado
el lease.

La recuperación no debe permitir dos workers procesando simultáneamente
el mismo job dentro del mismo lease.

## 8. Reintentos e idempotencia

Los reintentos deben distinguir entre:

-   errores transitorios;
-   errores permanentes;
-   efectos externos ya ejecutados.

El backoff debe ser exponencial y acotado.

Una operación con efecto externo debe utilizar una clave idempotente
estable. En particular:

-   renderizado;
-   generación de artefactos;
-   publicación;
-   creación de registros derivados.

Un retry nunca debe asumir que una operación externa no ocurrió
solamente porque el worker perdió conexión.

## 9. Ejecución por etapas

Cada job debe producir trazabilidad de sus etapas principales.

Ejemplo:

``` text
job
 ├── script
 ├── chaptering
 ├── tts
 ├── timing
 ├── render
 └── publish
```

Cada stage execution debe registrar al menos:

-   nombre de etapa;
-   estado;
-   inicio;
-   finalización;
-   duración;
-   intento;
-   error;
-   metadata operacional mínima.

Esto permite distinguir un job lento de un job bloqueado y medir qué
componentes consumen más recursos.

## 10. Arquitectura de pipelines

El worker no debe contener lógica específica de H1/H2/H2b.

Se define conceptualmente una interfaz:

``` python
class Pipeline:
    name: str

    def execute(self, job_context) -> PipelineResult:
        ...
```

Cada pipeline debe registrarse mediante un registry.

El worker:

1.  reclama el job;
2.  resuelve el pipeline por nombre;
3.  construye el contexto;
4.  ejecuta;
5.  persiste resultado/estado;
6.  registra métricas.

Agregar H3 no debe requerir modificar el algoritmo de scheduling o
locking del worker.

## 11. Separación arquitectónica

La evolución debe reforzar una separación conceptual:

``` text
Domain
  └── job states, pipeline contracts, value objects

Application
  └── use cases, orchestration, retry/recovery policies

Infrastructure
  └── Supabase, Storage, FFmpeg, TTS, Whisper, Claude, publishers

API
  └── HTTP boundary

Worker
  └── execution loop
```

No se exige una reescritura completa del proyecto. La separación se
introduce de forma incremental alrededor de los nuevos contratos.

## 12. Observabilidad

El sistema debe producir:

### Logs estructurados

Cada log relevante debe poder asociarse a:

-   job_id;
-   pipeline;
-   stage;
-   attempt;
-   worker_id;
-   resultado.

No se debe registrar información sensible ni secretos.

### Métricas

Como mínimo:

-   jobs procesados;
-   jobs completados;
-   jobs fallidos;
-   retries;
-   jobs recuperados;
-   queue depth;
-   duración por job;
-   duración por stage;
-   errores por pipeline;
-   API latency;
-   publicaciones exitosas/fallidas.

La instrumentación debe quedar preparada para Prometheus/Grafana, aunque
el despliegue de Grafana puede ser posterior.

## 13. Dashboard operacional

El dashboard debe dejar de mostrar únicamente el resultado final y
permitir inspeccionar ejecución.

Debe incluir, como mínimo:

-   estado actual del job;
-   pipeline;
-   intento;
-   timestamps;
-   duración;
-   stage actual;
-   error resumido;
-   resultado de publicación.

No se requiere un sistema de observabilidad completo dentro de React; el
dashboard es una vista operacional del backend.

## 14. Analytics y scheduling adaptativo

El scheduler existente conserva su lógica de retención:

-   =60% → 12h;

-   40--60% → 24h;

-   \<40% → 48h;

-   \<20% → drop;

-   sin métricas dentro de 24h → cadence lenta.

La evolución debe separar:

1.  captura de performance;
2.  interpretación;
3.  decisión de scheduling.

El scheduler no debe consultar directamente APIs externas ni conocer
detalles de cada plataforma.

Una capa de analytics/adapters debe normalizar métricas antes de que
sean consumidas por la política de scheduling.

## 15. Persistencia

Los cambios de base de datos deben ser aditivos.

Antes de agregar columnas o tablas se debe inspeccionar el esquema real
existente y reutilizar estructuras compatibles.

El diseño contempla conceptualmente:

-   metadata de ejecución de jobs;
-   leases;
-   intentos;
-   ejecuciones por stage;
-   claves idempotentes;
-   resultados de publicación;
-   métricas normalizadas.

Los nombres exactos y tipos deben quedar definidos en la migración del
plan, no inventarse contra un esquema no inspeccionado.

## 16. Seguridad

-   Las credenciales de plataforma permanecen del lado servidor.
-   El dashboard no recibe service-role keys.
-   Logs no deben exponer tokens.
-   Idempotency keys no deben contener secretos.
-   Las métricas deben excluir contenido sensible.
-   Las operaciones administrativas deben continuar protegidas por API
    key/auth existente.

## 17. Testing

Se requiere cobertura TDD para:

-   transición de estados;
-   claim/lease;
-   recovery;
-   retry/backoff;
-   idempotencia;
-   stage execution;
-   pipeline registry;
-   scheduler;
-   publicación;
-   fallos parciales;
-   integración API-worker-database.

Los tests existentes deben conservarse.

## 18. Criterios de aceptación

El incremento se considera terminado cuando:

1.  un job puede ser reclamado por un único worker;
2.  un lease expirado puede recuperarse;
3.  un fallo transitorio puede reintentarse;
4.  un fallo permanente termina en `failed`;
5.  un retry no duplica un efecto idempotente;
6.  cada etapa crítica deja trazabilidad;
7.  existen métricas mínimas de operación;
8.  el dashboard permite diagnosticar una ejecución;
9.  H1, H2 y H2b continúan funcionando;
10. el scheduler puede consumir métricas normalizadas sin acoplarse a
    una plataforma concreta;
11. la arquitectura permite registrar un pipeline nuevo sin modificar el
    worker core.

## 19. Decisiones deliberadas

-   No agregar otro pipeline todavía.
-   No introducir Redis/RabbitMQ todavía.
-   No reescribir todo el proyecto para imponer Clean Architecture.
-   No construir ML de optimización.
-   No mezclar analytics de plataforma con la lógica de ejecución.
-   Priorizar confiabilidad, observabilidad e idempotencia antes que
    volumen de features.

## 20. Siguiente paso

Ejecutar `superpowers:writing-plans` sobre este diseño y producir un
plan TDD dividido en tareas pequeñas, verificables y con commits
independientes.
