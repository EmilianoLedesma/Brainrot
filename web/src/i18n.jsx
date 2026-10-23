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
        "A short-form video pipeline. Generate stories, review finished videos, and publish from your own workspace.",
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
        { no: "02", name: "Script", note: "Your selected model writes hook, body, close. Built to be heard, not read." },
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
          blurb: "Give it a topic or a wild premise. It builds a story around your idea, narrates it over a looping background, and captions it a word at a time.",
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
              ["`BRAINROT_LLM_PROVIDER`", "Default integration for jobs without a Model choice: claude-code or codex. Restart the worker after changing this default."],
              ["`ANTHROPIC_API_KEY`", "Only required for the explicitly selected anthropic API provider."],
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
            { type: "code", text: "uvicorn brainrot.api:app --port 8001   # the API this UI talks to\npython -m brainrot.worker              # claims jobs, renders, paces, publishes" },
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
            { q: "Do I need to approve anything before a video goes out?", a: "A new YouTube connection uses reviewed uploads. Choose a finished video in the YouTube page, edit its details and visibility, then upload. Connecting your channel does not publish the existing queue. Previously configured automatic publishing keeps its existing behavior." },
            { q: "Why is my job stuck on pending?", a: "Nothing is consuming the queue. Jobs are claimed by the worker process, so start it with python -m brainrot.worker. Until then rows sit at pending indefinitely." },
            { q: "A job failed. Where do I look?", a: "The queue shows a short explanation. Inspect shows which step needs attention. Technical diagnostics are available in your browser’s developer tools, under Network, and in worker logs." },
            { q: "Can I run more than one worker?", a: "Yes. Claiming a job is conditioned on the row still being pending, so two workers racing for the same job leave exactly one winner. Rendering is CPU-bound, so this mostly helps if you have cores to spare." },
          ],
        },
        {
          title: "Output",
          items: [
            { q: "Why is the gallery empty?", a: "Nothing has rendered yet. Clips and chapters appear the moment a worker finishes one. If jobs are completing but nothing shows, check that a background clip exists — H2 and H2b cannot render without one." },
            { q: "Where do backgrounds come from?", a: "You supply them. Upload looping, copyright-free clips with python -m brainrot.cli add-background FILE. New stories take turns through the active backgrounds; chapters and retries keep the same choice." },
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
      headings: { new: "Start a job", queue: "Live queue", output: "Finished output", insights: "Find the drop" },
      tabs: { new: "New job", queue: "Queue", output: "Output", insights: "Insights" },
      steps: ["Pipeline", "Input", "Review"],
      model: { label: "Model", hint: "Uses this integration’s configured model and your local sign-in.", workerDefault: "Worker default" },
      motion: { label: "Motion graphics edit", hint: "Off: the main flow narrates over a background clip. On: same script and narration, animated with keyword punches and transitions instead of a clip.", on: "Motion graphics", off: "Main flow (background clip)" },
      brainrot: {
        label: "Brainrot level", low: "Grounded", high: "Max brainrot",
        levels: [
          { name: "Grounded", description: "No internet slang. Clear, straightforward storytelling." },
          { name: "Playful", description: "Light internet slang, a few jokes and a little weirdness." },
          { name: "Chaotic", description: "Regular internet slang, fast jokes and dramatic comparisons." },
          { name: "Unhinged", description: "Heavy internet slang, surreal imagery and ridiculous metaphors." },
          { name: "Max brainrot", description: "Internet slang throughout. Real topics stay factual; invented premises get wildly absurd." },
        ],
      },
      pipelines: {
        brainrot: { name: "Generate", tagline: "From a topic", blurb: "Your selected model writes a script, narrated over a background clip.", field: "Topic", hint: "Real topics stay factual; invented premises become fiction. Brainrot level sets how wild the delivery gets." },
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
      pagination: { label: "Queue pages", page: "Page", of: "of", previous: "Previous", next: "Next" },
      actions: "Job actions",
      retry: { label: "Retry", busy: "Retrying…", queued: "Queued again. Saved progress will be reused." },
      errors: {
        narration: "Narration couldn’t be generated. Please try again later.",
        background: "A background video couldn’t be loaded. Please try again later.",
        timeout: "This took longer than expected. Please try again.",
        model: "Your selected model is unavailable. Try another model or try again later.",
        connection: "We couldn’t connect. Please try again shortly.",
        render: "The video couldn’t be created. Please try again.",
        source: "We couldn’t process this video. Check the link and try again.",
        publishing: "This video is still being published. Please wait before deleting it.",
        retryUnavailable: "This job can’t be retried right now. Check its latest status.",
        publishingFailed: "The video couldn’t be published. Check the connected account before trying again.",
        missing: "This job is no longer available. Refresh the queue.",
        access: "Access to this workspace couldn’t be verified. Refresh and try again.",
        input: "Check your input and try again.",
        failed: "We couldn’t finish this job. Please try again.",
      },
      remove: {
        label: "Delete", confirmButton: "Confirm delete", cancel: "Cancel", busy: "Deleting…",
        confirm: "Permanently delete this job, its history and all output files? This cannot be undone.",
        title: "Delete job?", runningTitle: "Delete running job?",
        running: "Further work will stop. Any output still being saved will also be removed.",
      },
      execution: {
        title: "Execution", loading: "Reading stage history…", inspect: "Inspect", close: "Close",
        attempt: "Attempt", started: "Started", finished: "Finished", retryAt: "Retry after",
        stage: "Stage", stages: "Current stages", status: "Status", elapsed: "Duration",
        publications: "Publication queue", platform: "Platform", scheduled: "Scheduled", published: "Published",
        noStages: "Stages will appear when this attempt starts.",
        noPublications: "Publications appear when a clip or chapter is ready.",
        stale: "Showing the last update; connection interrupted.",
        names: { script: "Script", chaptering: "Chapters", background: "Background", tts: "Narration",
          render: "Render", upload: "Save media", schedule: "Schedule", download: "Source download",
          transcribe: "Transcript", selection: "Clip selection" },
      },
      jobsLabel: "Jobs",
      unreachable: "Connection interrupted",
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
        "Una fábrica de video vertical. Genera historias, revisa videos terminados y publica desde tu espacio de trabajo.",
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
        { no: "02", name: "Guion", note: "El modelo elegido escribe gancho, desarrollo y cierre. Para oírse, no para leerse." },
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
          blurb: "Dale un tema o una premisa disparatada. Crea una historia a partir de tu idea, la narra sobre un fondo en loop y la subtitula palabra por palabra.",
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
              ["`BRAINROT_LLM_PROVIDER`", "Integración para trabajos sin elección de Modelo: claude-code o codex. Reinicia el worker si cambias este valor."],
              ["`ANTHROPIC_API_KEY`", "Solo se necesita si eliges explícitamente el proveedor API anthropic."],
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
            { type: "code", text: "uvicorn brainrot.api:app --port 8001   # la API con la que habla esta interfaz\npython -m brainrot.worker              # toma jobs, renderiza, dosifica, publica" },
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
            { q: "¿Tengo que aprobar algo antes de que salga un video?", a: "Una conexión nueva de YouTube usa subidas revisadas. Elige un video terminado en YouTube, edita sus detalles y visibilidad y súbelo. Conectar tu canal no publica la cola existente. La publicación automática configurada anteriormente conserva su comportamiento." },
            { q: "¿Por qué mi job se queda en pending?", a: "Nada está consumiendo la cola. Los jobs los reclama el proceso worker, así que arráncalo con python -m brainrot.worker. Hasta entonces las filas se quedan en pending indefinidamente." },
            { q: "Falló un job. ¿Dónde reviso?", a: "La cola muestra una explicación breve. Inspeccionar muestra qué etapa necesita atención. Los detalles técnicos están en las herramientas de desarrollo del navegador, en Red, y en los registros del worker." },
            { q: "¿Puedo correr más de un worker?", a: "Sí. Reclamar un job está condicionado a que la fila siga en pending, así que dos workers compitiendo por el mismo job dejan exactamente un ganador. Renderizar satura CPU, así que esto ayuda sobre todo si te sobran núcleos." },
          ],
        },
        {
          title: "Resultados",
          items: [
            { q: "¿Por qué está vacía la galería?", a: "Todavía no se ha renderizado nada. Los clips y capítulos aparecen en cuanto un worker termina uno. Si los jobs se completan pero no ves nada, revisa que exista un clip de fondo — H2 y H2b no pueden renderizar sin uno." },
            { q: "¿De dónde salen los fondos?", a: "Los pones tú. Sube clips en loop libres de copyright con python -m brainrot.cli add-background FILE. Las historias nuevas alternan entre los fondos activos; los capítulos y reintentos conservan el mismo fondo." },
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
      headings: { new: "Lanzar un job", queue: "Cola en vivo", output: "Resultados", insights: "Encuentra la caída" },
      tabs: { new: "Nuevo job", queue: "Cola", output: "Resultados", insights: "Análisis" },
      steps: ["Pipeline", "Entrada", "Revisión"],
      model: { label: "Modelo", hint: "Usa el modelo configurado en esta integración y tu sesión local.", workerDefault: "Predeterminado del worker" },
      motion: { label: "Edición con motion graphics", hint: "Apagado: el flujo principal narra sobre un clip de fondo. Encendido: mismo guion y narración, animados con palabras clave y transiciones en vez de un clip.", on: "Motion graphics", off: "Flujo principal (clip de fondo)" },
      brainrot: {
        label: "Nivel de brainrot", low: "Tranquilo", high: "Brainrot máximo",
        levels: [
          { name: "Tranquilo", description: "Sin jerga de internet. Narración clara y directa." },
          { name: "Juguetón", description: "Un poco de jerga de internet, humor y rareza." },
          { name: "Caótico", description: "Jerga de internet frecuente, chistes rápidos y comparaciones dramáticas." },
          { name: "Desquiciado", description: "Mucha jerga de internet, imágenes surrealistas y metáforas ridículas." },
          { name: "Brainrot máximo", description: "Jerga de internet por todos lados. Los temas reales conservan los hechos; las premisas inventadas se vuelven absurdas." },
        ],
      },
      pipelines: {
        brainrot: { name: "Generar", tagline: "Desde un tema", blurb: "El modelo elegido escribe el guion y se narra sobre un clip de fondo.", field: "Tema", hint: "Los temas reales conservan los hechos; las premisas inventadas se vuelven ficción. El nivel de brainrot controla lo disparatado de la narración." },
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
      pagination: { label: "Páginas de la cola", page: "Página", of: "de", previous: "Anterior", next: "Siguiente" },
      actions: "Acciones del job",
      retry: { label: "Reintentar", busy: "Reintentando…", queued: "Encolado de nuevo. Se reutilizará el progreso guardado." },
      errors: {
        narration: "No se pudo generar la narración. Inténtalo más tarde.",
        background: "No se pudo cargar un video de fondo. Inténtalo más tarde.",
        timeout: "Esto tardó más de lo esperado. Inténtalo de nuevo.",
        model: "El modelo elegido no está disponible. Prueba otro modelo o inténtalo más tarde.",
        connection: "No pudimos conectarnos. Inténtalo en unos momentos.",
        render: "No se pudo crear el video. Inténtalo de nuevo.",
        source: "No pudimos procesar este video. Revisa el enlace e inténtalo de nuevo.",
        publishing: "Este video se está publicando. Espera antes de eliminarlo.",
        retryUnavailable: "No se puede reintentar este job ahora. Revisa su estado actual.",
        publishingFailed: "No se pudo publicar el video. Revisa la cuenta conectada antes de volver a intentar.",
        missing: "Este job ya no está disponible. Actualiza la cola.",
        access: "No se pudo verificar el acceso. Actualiza e inténtalo de nuevo.",
        input: "Revisa los datos e inténtalo de nuevo.",
        failed: "No pudimos completar este job. Inténtalo de nuevo.",
      },
      remove: {
        label: "Eliminar", confirmButton: "Confirmar eliminación", cancel: "Cancelar", busy: "Eliminando…",
        confirm: "¿Eliminar permanentemente este job, su historial y todos sus archivos de salida? No se puede deshacer.",
        title: "¿Eliminar job?", runningTitle: "¿Eliminar job en ejecución?",
        running: "Se detendrá el trabajo pendiente. También se eliminará cualquier resultado que se esté guardando.",
      },
      execution: {
        title: "Ejecución", loading: "Cargando historial de etapas…", inspect: "Inspeccionar", close: "Cerrar",
        attempt: "Intento", started: "Inicio", finished: "Fin", retryAt: "Reintentar después",
        stage: "Etapa", stages: "Etapas actuales", status: "Estado", elapsed: "Duración",
        publications: "Cola de publicación", platform: "Plataforma", scheduled: "Programado", published: "Publicado",
        noStages: "Las etapas aparecerán cuando empiece este intento.",
        noPublications: "Las publicaciones aparecen cuando un clip o capítulo está listo.",
        stale: "Se muestra la última actualización; conexión interrumpida.",
        names: { script: "Guion", chaptering: "Capítulos", background: "Fondo", tts: "Narración",
          render: "Render", upload: "Guardar media", schedule: "Programar", download: "Descargar origen",
          transcribe: "Transcripción", selection: "Selección de clips" },
      },
      jobsLabel: "Jobs",
      unreachable: "Conexión interrumpida",
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
