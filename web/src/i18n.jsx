import React, { createContext, useContext, useEffect, useState } from "react";

/* All page copy lives here in both languages. Docs bodies are stored as blocks
   rather than JSX so a translation never has to touch markup, and so code,
   commands, table keys and enum values stay identical across languages. */

const STORAGE_KEY = "brainrot.lang";

export const COPY = {
  en: {
    langButton: "Hablar español",
    langFlag: "ES",
    langTitle: "Yes, the whole site speaks Spanish too",
    nav: { home: "Home", docs: "Docs", faq: "FAQ", workspace: "Workspace" },

    footer: {
      blurb:
        "An automated short-form video pipeline. Built and operated by one person, with no review step anywhere in it.",
      product: "Product",
      resources: "Resources",
      builtWith: "Built with",
      overview: "Overview",
      workspace: "Workspace",
      docs: "Documentation",
      faq: "FAQ",
      note: "Single-operator build · not a hosted service",
    },

    home: {
      stickers: ["runs itself", "one operator", "zero edits"],
      titleA: "Feed the",
      titleMark: "machine",
      titleB: "it does the rest.",
      lede:
        "Three pipelines that turn a link, a topic, or a subreddit into finished vertical video — then post it themselves. Script, voice, captions, crop, schedule. Nobody reviews anything.",
      ctaPrimary: "Start a job →",
      ctaSecondary: "Read the docs",
      specs: [
        { value: "9:16", label: "Every single frame" },
        { value: "3", label: "Platforms, one queue" },
        { value: "0", label: "Approvals needed" },
        { value: "12h", label: "Fastest chapter gap" },
      ],
      lineLabel: "The line",
      lineTitleA: "Five stages,",
      lineTitleB: "no hands",
      stages: [
        { no: "01", name: "Source", note: "A topic, a YouTube link, or a subreddit that cleared its bar." },
        { no: "02", name: "Script", note: "Claude writes hook, body, close. Built to be heard, not read." },
        { no: "03", name: "Voice", note: "Narration with a timing event on every single word." },
        { no: "04", name: "Render", note: "Looping background, 9:16 crop that follows the face, captions burned in." },
        { no: "05", name: "Post", note: "Queued per platform, paced by how the last one did." },
      ],
      intakeLabel: "Intake",
      intakeTitleA: "Three ways",
      intakeTitleB: "in",
      sources: [
        {
          idx: "H1", kind: "repurpose", title: "Repurpose",
          blurb: "Hand it a long video. It reads the transcript, picks the moments that survive without context, and reframes each one to vertical while following whoever is talking.",
          points: [
            "YouTube captions when they exist, Whisper when they don't",
            "Face tracking, smoothed so the frame never wobbles",
            "Cuts scored on whether a scrolling viewer would stay",
          ],
        },
        {
          idx: "H2", kind: "brainrot", title: "Generate",
          blurb: "Give it a subject. It finds the one genuinely interesting thing about it, narrates that over a looping background, and captions it a word at a time.",
          points: [
            "Caption timing straight from the synthesizer, not guessed",
            "Backgrounds pulled from your own clip library",
            "Hook, body, close. Never a preamble",
          ],
        },
        {
          idx: "H2b", kind: "reddit", title: "Narrate",
          blurb: "Point it at subreddits and a quality bar. It retells posts that clear it, keeping every event intact while cutting the rambling, and splits long ones into chapters.",
          points: [
            "Filtered on upvotes, comments, age and length",
            "A post can never be narrated twice",
            "Chapters released on evidence, not on a timer",
          ],
        },
      ],
      releaseLabel: "Release",
      releaseTitleA: "Chapters",
      releaseTitleMid: "earn",
      releaseTitleB: "the next slot",
      releaseBody:
        "Chapter one goes out immediately. Everything after it waits on the retention the last one actually got: finish rates above sixty percent buy twelve hours, the middle band gets a day, weak ones get two. Below twenty percent the story stops. A series nobody finishes never gets to flood the feed.",
      releaseCta: "Common questions →",
      finalTitleA: "Queue it and",
      finalMark: "walk away",
      finalCta: "Open the workspace →",
    },

    docs: {
      label: "Reference",
      title: "Docs",
      lede:
        "How to stand the thing up, what every environment variable does, and the shape of the data underneath.",
      sections: [
        {
          id: "setup",
          title: "Setup",
          blocks: [
            { type: "p", text: "Everything persistent lives in Supabase: rows in Postgres, media in the `media` storage bucket. Nothing on local disk is expected to survive a job." },
            { type: "ol", items: [
              "Create a Supabase project.",
              "Apply `migrations/001_init.sql` — it creates five enums, ten tables, the indexes, row level security, and the private bucket.",
              "Copy `.env.example` to `.env` and fill it in.",
              "`pip install -r requirements.txt`",
              "`python test_db.py` should print `phase 0 ok`.",
            ] },
            { type: "callout", strong: "Use the pooler connection.", text: "The direct host `db.PROJECT-REF.supabase.co` only publishes an AAAA record and is unreachable from IPv4-only networks. Point `DATABASE_URL` at `aws-0-REGION.pooler.supabase.com`, whose user is `postgres.PROJECT-REF`, and percent-encode the password." },
          ],
        },
        {
          id: "env",
          title: "Environment",
          blocks: [
            { type: "table", head: ["Variable", "What it is"], rows: [
              ["`SUPABASE_URL`", "Project URL."],
              ["`SUPABASE_SERVICE_KEY`", "Service role key. Bypasses RLS — server side only, never in a browser."],
              ["`MEDIA_BUCKET`", "Storage bucket for every generated and downloaded file."],
              ["`ANTHROPIC_API_KEY`", "Claude, for scripts, Reddit rewrites and clip selection."],
              ["`DATABASE_URL`", "Postgres via the session pooler. Used only to apply migrations."],
              ["`DASHBOARD_API_KEY`", "Shared secret for this UI. The API rejects everything while it is unset."],
              ["`DASHBOARD_ORIGINS`", "Comma-separated origins allowed to call the API."],
              ["`REDDIT_CLIENT_ID`", "Reddit script app. Public reads only, so no username or password."],
              ["`WHISPER_MODEL`", "Only used when a YouTube video has no captions of its own."],
            ] },
          ],
        },
        {
          id: "running",
          title: "Running it",
          blocks: [
            { type: "p", text: "Two long-running processes, plus commands you run by hand." },
            { type: "code", text: "uvicorn brainrot.api:app --port 8000   # the API this UI talks to\npython -m brainrot.worker              # claims jobs, renders, paces, publishes" },
            { type: "table", head: ["Command", "Does"], rows: [
              ["`cli add-background FILE`", "Uploads a looping background clip. H2 and H2b need at least one."],
              ["`cli scan-reddit`", "Queues jobs for subreddit posts that clear their bar."],
              ["`cli tick`", "Runs a pacing pass and lists what is due."],
              ["`cli publish`", "Uploads everything currently due."],
              ["`python test_pipeline.py`", "Offline checks. No credentials, no network."],
            ] },
          ],
        },
        {
          id: "api",
          title: "API",
          blocks: [
            { type: "p", text: "Three endpoints, all behind the `X-API-Key` header. Reads go through here rather than straight from the browser to Supabase, because every table has RLS on with no policies." },
            { type: "table", head: ["Endpoint", "Shape"], rows: [
              ["`POST /jobs`", "`{kind, topic}` or `{kind, youtube_url}` returns `{id}`"],
              ["`GET /jobs`", "Newest first, capped at 200."],
              ["`GET /gallery`", "Ready clips and chapters merged, each with a signed URL valid one hour."],
            ] },
          ],
        },
        {
          id: "model",
          title: "Data model",
          blocks: [
            { type: "p", text: "A job produces clips (H1) or a story (H2 and H2b); a story splits into chapters; each chapter accumulates metrics; clips and chapters end up in publications." },
            { type: "table", head: ["Enum", "Values"], rows: [
              ["`job_kind`", "repurpose · brainrot · reddit"],
              ["`job_status`", "pending · running · done · failed · cancelled"],
              ["`asset_status`", "pending · rendering · ready · failed"],
              ["`publication_status`", "scheduled · uploading · published · failed"],
              ["`platform`", "youtube · tiktok · instagram"],
            ] },
          ],
        },
        {
          id: "publishing",
          title: "Publishing",
          blocks: [
            { type: "p", text: "There is no OAuth consent flow in the code. Registering each developer app is a manual, browser-bound step; the publisher reads whatever tokens are in `platform_credentials` and skips any platform without a row, so the worker keeps running while apps are pending." },
            { type: "code", text: 'db.client().table("platform_credentials").upsert({\n    "platform": "youtube",\n    "data": {"access_token": "...", "refresh_token": "...",\n             "client_id": "...", "client_secret": "..."},\n}, on_conflict="platform").execute()' },
            { type: "callout", strong: "Two platform facts.", text: "TikTok forces every post from an unaudited client to private. YouTube has no API field that declares a Short — a vertical video under three minutes simply becomes one." },
          ],
        },
      ],
    },

    faq: {
      label: "Answers",
      titleA: "Questions,",
      titleB: "answered",
      lede: "What the system does, what it refuses to do, and the parts that are not finished yet.",
      groups: [
        {
          title: "Running it",
          items: [
            { q: "Do I need to approve anything before a video goes out?", a: "No, and there is no way to. There is no review step anywhere in the pipeline — a job that finishes rendering is queued for publishing on its own. If you want a human gate, that is a feature nobody has built." },
            { q: "Why is my job stuck on pending?", a: "Nothing is consuming the queue. Jobs are claimed by the worker process, so start it with python -m brainrot.worker. Until then rows sit at pending indefinitely." },
            { q: "A job failed. Where do I look?", a: "The traceback is written onto the job row itself and shown under the input in the queue table. The worker records it before re-raising, so a failure is never silent." },
            { q: "Can I run more than one worker?", a: "Yes. Claiming a job is conditioned on the row still being pending, so two workers racing for the same job leave exactly one winner. Rendering is CPU-bound, so this mostly helps if you have cores to spare." },
          ],
        },
        {
          title: "Output",
          items: [
            { q: "Why is the gallery empty?", a: "Nothing has rendered yet. Clips and chapters appear the moment a worker finishes one. If jobs are completing but nothing shows, check that a background clip exists — H2 and H2b cannot render without one." },
            { q: "Where do backgrounds come from?", a: "You supply them. Upload looping, copyright-free clips with python -m brainrot.cli add-background FILE, and one is picked at random per story." },
            { q: "How are the captions timed?", a: "For generated stories, the speech synthesizer reports a timing event per spoken word, so the captions are exact rather than estimated. For repurposed video the timings come from the source captions, or from Whisper when the video has none." },
            { q: "Why 1080 × 1920 for everything?", a: "It is the shape all three platforms want. The renderer scales and crops to it rather than letterboxing, so nothing ships with bars." },
          ],
        },
        {
          title: "Publishing",
          items: [
            { q: "Can it post right now?", a: "Only once you register the developer apps. The uploaders for YouTube, TikTok and Instagram are written, but there is no OAuth consent flow — that step is manual and browser-bound. Platforms without a credentials row are skipped, so the worker keeps running regardless." },
            { q: "Why did my TikTok post come out private?", a: "TikTok forces every post from an unaudited client to private viewing. That is their restriction, not a setting in this code. It lifts when your app passes their audit." },
            { q: "How does it decide when to post the next chapter?", a: "On the previous chapter's retention. Above sixty percent the next one follows in twelve hours, the middle band waits a day, weak ones two. Below twenty percent the story is dropped rather than given more slots. If the platforms report nothing within a day, it falls back to the slowest cadence instead of stalling." },
            { q: "Does a failed upload retry automatically?", a: "No, deliberately. An upload that times out after the platform already accepted it would post the same video twice. Failures stay failed until you re-queue them by hand." },
          ],
        },
        {
          title: "Data and access",
          items: [
            { q: "Is this dashboard safe to expose?", a: "Treat it as private. The shared secret is baked into the JavaScript bundle at build time, which makes it a gate against casual access, not an authentication boundary. Serve it somewhere only you can reach." },
            { q: "Why does the queue poll instead of using live updates?", a: "Live updates from the browser would require read policies for anonymous users on the jobs table, and the anonymous key ships in the bundle. That would make your data readable by anyone with the project URL. Reading through the API keeps row level security closed." },
            { q: "Where is the media stored?", a: "A private Supabase bucket. The gallery plays it through signed URLs that expire after an hour, so no file is ever publicly addressable." },
          ],
        },
      ],
      ctaTitle: "Still",
      ctaMark: "curious",
      ctaBody: "The docs cover setup, every environment variable, the endpoints and the data model.",
      ctaButton: "Read the docs →",
    },

    work: {
      label: "Workspace",
      headings: { new: "Start a job", queue: "Live queue", output: "Finished output" },
      tabs: { new: "New job", queue: "Queue", output: "Output" },
      steps: ["Pipeline", "Input", "Review"],
      pipelines: {
        brainrot: { name: "Generate", tagline: "From a topic", blurb: "Claude writes the script, it gets narrated over a background clip.", field: "Topic", hint: "One subject. The script finds the single most interesting thing about it." },
        repurpose: { name: "Repurpose", tagline: "From a YouTube link", blurb: "Transcribed, cut into standalone moments, reframed to follow the speaker.", field: "Source URL", hint: "Long-form works best. Up to three clips come out of one video." },
      },
      note: "H2b runs on its own schedule from reddit_sources_config and is not triggered here.",
      back: "← Back",
      review: "Review →",
      edit: "← Edit",
      queueIt: "Queue it",
      queueing: "Queueing…",
      reviewWarn: "Once queued this runs unattended and publishes without another prompt.",
      queuedLabel: "Queued",
      queuedTitle: "In the queue",
      queuedBody: "is waiting. A worker will claim it and move it to running; it stays pending until one is listening.",
      queuedAgain: "Queue another",
      colPipeline: "Pipeline",
      colInput: "Input",
      colStatus: "Status",
      colQueued: "Queued",
      jobsLabel: "Jobs",
      unreachable: "API unreachable",
      reading: "Reading",
      readingQueue: "Fetching the queue…",
      readingOutput: "Fetching output…",
      emptyQueue: "Queue empty",
      emptyQueueBody: "Nothing has been submitted yet.",
      emptyOutput: "Nothing rendered",
      emptyOutputBody: "Finished clips and chapters land here as soon as a worker produces one.",
    },
  },

  es: {
    langButton: "Hablar gringo",
    langFlag: "EN",
    langTitle: "Volver al inglés, por si lo extrañabas",
    nav: { home: "Inicio", docs: "Docs", faq: "Dudas", workspace: "Taller" },

    footer: {
      blurb:
        "Una fábrica automática de video vertical. Construida y operada por una sola persona, sin un solo paso de revisión en medio.",
      product: "Producto",
      resources: "Recursos",
      builtWith: "Hecho con",
      overview: "Resumen",
      workspace: "Taller",
      docs: "Documentación",
      faq: "Dudas",
      note: "Proyecto de un solo operador · no es un servicio",
    },

    home: {
      stickers: ["se opera solo", "un operador", "cero ediciones"],
      titleA: "Alimenta la",
      titleMark: "máquina",
      titleB: "ella hace lo demás.",
      lede:
        "Tres pipelines que convierten un link, un tema o un subreddit en video vertical terminado — y lo publican solas. Guion, voz, subtítulos, encuadre, calendario. Nadie revisa nada.",
      ctaPrimary: "Lanzar un job →",
      ctaSecondary: "Leer la documentación",
      specs: [
        { value: "9:16", label: "Cada cuadro, sin excepción" },
        { value: "3", label: "Plataformas, una cola" },
        { value: "0", label: "Aprobaciones necesarias" },
        { value: "12h", label: "Intervalo mínimo entre capítulos" },
      ],
      lineLabel: "La línea",
      lineTitleA: "Cinco etapas,",
      lineTitleB: "sin manos",
      stages: [
        { no: "01", name: "Fuente", note: "Un tema, un link de YouTube o un subreddit que pasó su filtro." },
        { no: "02", name: "Guion", note: "Claude escribe gancho, desarrollo y cierre. Para oírse, no para leerse." },
        { no: "03", name: "Voz", note: "Narración con una marca de tiempo en cada palabra." },
        { no: "04", name: "Render", note: "Fondo en loop, recorte 9:16 que sigue la cara, subtítulos quemados." },
        { no: "05", name: "Publicar", note: "En cola por plataforma, al ritmo que marcó el capítulo anterior." },
      ],
      intakeLabel: "Entradas",
      intakeTitleA: "Tres formas de",
      intakeTitleB: "entrar",
      sources: [
        {
          idx: "H1", kind: "repurpose", title: "Reutilizar",
          blurb: "Dale un video largo. Lee la transcripción, elige los momentos que se sostienen sin contexto y reencuadra cada uno a vertical siguiendo a quien habla.",
          points: [
            "Subtítulos de YouTube cuando existen, Whisper cuando no",
            "Seguimiento de rostro, suavizado para que el cuadro no tiemble",
            "Cortes puntuados según si alguien dejaría de scrollear",
          ],
        },
        {
          idx: "H2", kind: "brainrot", title: "Generar",
          blurb: "Dale un tema. Encuentra lo único realmente interesante que tiene, lo narra sobre un fondo en loop y lo subtitula palabra por palabra.",
          points: [
            "Tiempos de subtítulo del sintetizador, no estimados",
            "Fondos sacados de tu propia librería de clips",
            "Gancho, desarrollo, cierre. Nunca un preámbulo",
          ],
        },
        {
          idx: "H2b", kind: "reddit", title: "Narrar",
          blurb: "Apúntalo a subreddits con un mínimo de calidad. Recuenta los posts que lo pasan, conservando cada hecho y cortando la paja, y parte los largos en capítulos.",
          points: [
            "Filtrado por upvotes, comentarios, antigüedad y longitud",
            "Un post nunca puede narrarse dos veces",
            "Capítulos liberados por evidencia, no por reloj",
          ],
        },
      ],
      releaseLabel: "Publicación",
      releaseTitleA: "Los capítulos",
      releaseTitleMid: "se ganan",
      releaseTitleB: "el siguiente turno",
      releaseBody:
        "El capítulo uno sale de inmediato. Todo lo demás espera a la retención que consiguió el anterior: arriba del sesenta por ciento compra doce horas, la franja media un día, los flojos dos. Por debajo del veinte por ciento la historia se abandona. Una serie que nadie termina nunca llega a inundar el feed.",
      releaseCta: "Preguntas frecuentes →",
      finalTitleA: "Déjalo en cola y",
      finalMark: "vete",
      finalCta: "Abrir el taller →",
    },

    docs: {
      label: "Referencia",
      title: "Docs",
      lede:
        "Cómo levantarlo, qué hace cada variable de entorno y la forma de los datos por debajo.",
      sections: [
        {
          id: "setup",
          title: "Instalación",
          blocks: [
            { type: "p", text: "Todo lo persistente vive en Supabase: filas en Postgres, media en el bucket `media`. Nada en disco local sobrevive a un job." },
            { type: "ol", items: [
              "Crea un proyecto de Supabase.",
              "Aplica `migrations/001_init.sql` — crea cinco enums, diez tablas, los índices, row level security y el bucket privado.",
              "Copia `.env.example` a `.env` y llénalo.",
              "`pip install -r requirements.txt`",
              "`python test_db.py` debe imprimir `phase 0 ok`.",
            ] },
            { type: "callout", strong: "Usa la conexión del pooler.", text: "El host directo `db.PROJECT-REF.supabase.co` solo publica un registro AAAA y es inalcanzable desde redes IPv4. Apunta `DATABASE_URL` a `aws-0-REGION.pooler.supabase.com`, cuyo usuario es `postgres.PROJECT-REF`, y codifica la contraseña en porcentaje." },
          ],
        },
        {
          id: "env",
          title: "Entorno",
          blocks: [
            { type: "table", head: ["Variable", "Qué es"], rows: [
              ["`SUPABASE_URL`", "URL del proyecto."],
              ["`SUPABASE_SERVICE_KEY`", "Llave service_role. Pasa por encima de RLS — solo del lado del servidor, nunca en un navegador."],
              ["`MEDIA_BUCKET`", "Bucket para cada archivo generado y descargado."],
              ["`ANTHROPIC_API_KEY`", "Claude, para guiones, reescritura de Reddit y selección de clips."],
              ["`DATABASE_URL`", "Postgres vía el session pooler. Solo para aplicar migraciones."],
              ["`DASHBOARD_API_KEY`", "Secreto compartido de esta interfaz. La API rechaza todo mientras esté vacío."],
              ["`DASHBOARD_ORIGINS`", "Orígenes separados por coma con permiso de llamar a la API."],
              ["`REDDIT_CLIENT_ID`", "App de tipo script en Reddit. Solo lecturas públicas, sin usuario ni contraseña."],
              ["`WHISPER_MODEL`", "Solo se usa cuando un video de YouTube no trae subtítulos propios."],
            ] },
          ],
        },
        {
          id: "running",
          title: "Ejecutarlo",
          blocks: [
            { type: "p", text: "Dos procesos permanentes, más comandos que corres a mano." },
            { type: "code", text: "uvicorn brainrot.api:app --port 8000   # la API con la que habla esta interfaz\npython -m brainrot.worker              # toma jobs, renderiza, dosifica, publica" },
            { type: "table", head: ["Comando", "Hace"], rows: [
              ["`cli add-background FILE`", "Sube un clip de fondo en loop. H2 y H2b necesitan al menos uno."],
              ["`cli scan-reddit`", "Encola jobs con los posts que pasan su filtro."],
              ["`cli tick`", "Corre una pasada de ritmo y lista lo que toca."],
              ["`cli publish`", "Sube todo lo que ya venció."],
              ["`python test_pipeline.py`", "Pruebas sin red ni credenciales."],
            ] },
          ],
        },
        {
          id: "api",
          title: "API",
          blocks: [
            { type: "p", text: "Tres endpoints, todos detrás del header `X-API-Key`. Las lecturas pasan por aquí en lugar de ir del navegador directo a Supabase, porque cada tabla tiene RLS activo y cero políticas." },
            { type: "table", head: ["Endpoint", "Forma"], rows: [
              ["`POST /jobs`", "`{kind, topic}` o `{kind, youtube_url}` devuelve `{id}`"],
              ["`GET /jobs`", "Más reciente primero, tope de 200."],
              ["`GET /gallery`", "Clips y capítulos listos, cada uno con una URL firmada válida una hora."],
            ] },
          ],
        },
        {
          id: "model",
          title: "Modelo de datos",
          blocks: [
            { type: "p", text: "Un job produce clips (H1) o una story (H2 y H2b); una story se parte en capítulos; cada capítulo acumula métricas; clips y capítulos terminan en publications." },
            { type: "table", head: ["Enum", "Valores"], rows: [
              ["`job_kind`", "repurpose · brainrot · reddit"],
              ["`job_status`", "pending · running · done · failed · cancelled"],
              ["`asset_status`", "pending · rendering · ready · failed"],
              ["`publication_status`", "scheduled · uploading · published · failed"],
              ["`platform`", "youtube · tiktok · instagram"],
            ] },
          ],
        },
        {
          id: "publishing",
          title: "Publicación",
          blocks: [
            { type: "p", text: "No hay flujo de consentimiento OAuth en el código. Registrar cada app de desarrollador es un paso manual que exige navegador; el publicador lee los tokens que haya en `platform_credentials` y salta cualquier plataforma sin fila, así el worker sigue corriendo mientras las apps están pendientes." },
            { type: "code", text: 'db.client().table("platform_credentials").upsert({\n    "platform": "youtube",\n    "data": {"access_token": "...", "refresh_token": "...",\n             "client_id": "...", "client_secret": "..."},\n}, on_conflict="platform").execute()' },
            { type: "callout", strong: "Dos detalles de plataforma.", text: "TikTok fuerza a privado todo lo que publique un cliente sin auditar. YouTube no tiene ningún campo de API que declare un Short — un video vertical de menos de tres minutos simplemente se vuelve uno." },
          ],
        },
      ],
    },

    faq: {
      label: "Respuestas",
      titleA: "Dudas,",
      titleB: "resueltas",
      lede: "Qué hace el sistema, qué se niega a hacer y qué partes todavía no están terminadas.",
      groups: [
        {
          title: "Operación",
          items: [
            { q: "¿Tengo que aprobar algo antes de que salga un video?", a: "No, y no hay manera de hacerlo. No existe ningún paso de revisión en el pipeline — un job que termina de renderizar se encola para publicar por su cuenta. Si quieres un freno humano, esa es una función que nadie construyó." },
            { q: "¿Por qué mi job se queda en pending?", a: "Nada está consumiendo la cola. Los jobs los reclama el proceso worker, así que arráncalo con python -m brainrot.worker. Hasta entonces las filas se quedan en pending indefinidamente." },
            { q: "Falló un job. ¿Dónde reviso?", a: "El traceback se escribe en la fila del job y se muestra debajo del input en la tabla de cola. El worker lo registra antes de relanzar la excepción, así que un fallo nunca es silencioso." },
            { q: "¿Puedo correr más de un worker?", a: "Sí. Reclamar un job está condicionado a que la fila siga en pending, así que dos workers compitiendo por el mismo job dejan exactamente un ganador. Renderizar satura CPU, así que esto ayuda sobre todo si te sobran núcleos." },
          ],
        },
        {
          title: "Resultados",
          items: [
            { q: "¿Por qué está vacía la galería?", a: "Todavía no se ha renderizado nada. Los clips y capítulos aparecen en cuanto un worker termina uno. Si los jobs se completan pero no ves nada, revisa que exista un clip de fondo — H2 y H2b no pueden renderizar sin uno." },
            { q: "¿De dónde salen los fondos?", a: "Los pones tú. Sube clips en loop libres de copyright con python -m brainrot.cli add-background FILE, y se elige uno al azar por historia." },
            { q: "¿Cómo se sincronizan los subtítulos?", a: "En las historias generadas, el sintetizador de voz reporta una marca de tiempo por palabra hablada, así que los subtítulos son exactos y no estimados. En el video reutilizado los tiempos vienen de los subtítulos originales, o de Whisper cuando el video no trae." },
            { q: "¿Por qué 1080 × 1920 para todo?", a: "Es la forma que quieren las tres plataformas. El renderizador escala y recorta a esa medida en vez de poner barras, así que nada sale con marco." },
          ],
        },
        {
          title: "Publicación",
          items: [
            { q: "¿Ya puede publicar?", a: "Solo cuando registres las apps de desarrollador. Los subidores de YouTube, TikTok e Instagram están escritos, pero no hay flujo de consentimiento OAuth — ese paso es manual y exige navegador. Las plataformas sin fila de credenciales se saltan, así que el worker sigue corriendo igual." },
            { q: "¿Por qué mi post de TikTok salió privado?", a: "TikTok fuerza a visibilidad privada todo lo que publique un cliente sin auditar. Es restricción de ellos, no un ajuste de este código. Se levanta cuando tu app pasa su auditoría." },
            { q: "¿Cómo decide cuándo publicar el siguiente capítulo?", a: "Por la retención del capítulo anterior. Arriba del sesenta por ciento el siguiente sale en doce horas, la franja media espera un día, los flojos dos. Por debajo del veinte por ciento la historia se abandona en vez de darle más turnos. Si las plataformas no reportan nada en un día, cae al ritmo más lento en lugar de quedarse atorado." },
            { q: "¿Un upload fallido se reintenta solo?", a: "No, a propósito. Un upload que se corta después de que la plataforma ya lo aceptó publicaría el mismo video dos veces. Los fallos se quedan en failed hasta que los reencolas a mano." },
          ],
        },
        {
          title: "Datos y acceso",
          items: [
            { q: "¿Es seguro exponer este panel?", a: "Trátalo como privado. El secreto compartido queda incrustado en el bundle de JavaScript al compilar, lo que lo vuelve una barrera contra curiosos, no una frontera de autenticación. Sírvelo donde solo tú llegues." },
            { q: "¿Por qué la cola hace polling en vez de usar tiempo real?", a: "El tiempo real desde el navegador exigiría políticas de lectura para usuarios anónimos sobre la tabla jobs, y la llave anónima viaja en el bundle. Eso dejaría tus datos legibles para cualquiera con la URL del proyecto. Leer a través de la API mantiene row level security cerrado." },
            { q: "¿Dónde se guarda la media?", a: "En un bucket privado de Supabase. La galería la reproduce con URLs firmadas que expiran en una hora, así ningún archivo queda públicamente direccionable." },
          ],
        },
      ],
      ctaTitle: "¿Sigues con",
      ctaMark: "curiosidad?",
      ctaBody: "La documentación cubre instalación, cada variable de entorno, los endpoints y el modelo de datos.",
      ctaButton: "Leer la documentación →",
    },

    work: {
      label: "Taller",
      headings: { new: "Lanzar un job", queue: "Cola en vivo", output: "Resultados" },
      tabs: { new: "Nuevo job", queue: "Cola", output: "Resultados" },
      steps: ["Pipeline", "Entrada", "Revisión"],
      pipelines: {
        brainrot: { name: "Generar", tagline: "Desde un tema", blurb: "Claude escribe el guion y se narra sobre un clip de fondo.", field: "Tema", hint: "Un solo asunto. El guion encuentra lo más interesante que tiene." },
        repurpose: { name: "Reutilizar", tagline: "Desde un link de YouTube", blurb: "Transcrito, cortado en momentos que se sostienen solos, reencuadrado siguiendo a quien habla.", field: "URL de origen", hint: "Funciona mejor con formato largo. De un video salen hasta tres clips." },
      },
      note: "H2b corre en su propio horario desde reddit_sources_config y no se lanza desde aquí.",
      back: "← Atrás",
      review: "Revisar →",
      edit: "← Editar",
      queueIt: "Encolar",
      queueing: "Encolando…",
      reviewWarn: "Una vez encolado corre sin supervisión y publica sin volver a preguntar.",
      queuedLabel: "Encolado",
      queuedTitle: "En la cola",
      queuedBody: "está esperando. Un worker lo reclamará y lo pasará a running; se queda en pending mientras ninguno escuche.",
      queuedAgain: "Encolar otro",
      colPipeline: "Pipeline",
      colInput: "Entrada",
      colStatus: "Estado",
      colQueued: "Encolado",
      jobsLabel: "Jobs",
      unreachable: "API inalcanzable",
      reading: "Leyendo",
      readingQueue: "Cargando la cola…",
      readingOutput: "Cargando resultados…",
      emptyQueue: "Cola vacía",
      emptyQueueBody: "Todavía no has enviado nada.",
      emptyOutput: "Nada renderizado",
      emptyOutputBody: "Los clips y capítulos terminados aparecen aquí en cuanto un worker produce uno.",
    },
  },
};

const LangContext = createContext(null);

export function LangProvider({ children }) {
  const [lang, setLang] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "en" || saved === "es") return saved;
    } catch {
      // Private mode or blocked storage: fall through to the browser's preference.
    }
    return navigator.language?.toLowerCase().startsWith("es") ? "es" : "en";
  });

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // Not worth failing a render over a rejected write.
    }
  }, [lang]);

  const toggle = () => setLang((prev) => (prev === "en" ? "es" : "en"));

  return (
    <LangContext.Provider value={{ lang, setLang, toggle, t: COPY[lang] }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang() {
  const value = useContext(LangContext);
  if (!value) throw new Error("useLang must be used inside LangProvider");
  return value;
}

/** Copy for the current language. */
export function useCopy() {
  return useLang().t;
}
