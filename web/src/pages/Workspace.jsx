import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { useCopy } from "../i18n.jsx";
import { GENERATION_PROVIDERS } from "../generation.js";
import { userError } from "../errors.js";
import Execution, { duration } from "./Execution.jsx";

/* The work surface. Submitting a job is a three-step flow rather than one form,
   because picking a pipeline and describing the input are different decisions and
   the review step is the last chance to catch a wrong paste.

   Pipeline ids, field keys and placeholders are backend contract, so they live
   here rather than in the translation tree. */

const FIELDS = {
  brainrot: { code: "H2", key: "topic", type: "text", placeholder: "roman empire silver crisis" },
  repurpose: { code: "H1", key: "youtube_url", type: "url", placeholder: "https://youtube.com/watch?v=..." },
};

function usePoll(path, intervalMs, timeoutMs = 15000) {
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);
  const [loaded, setLoaded] = useState(false);

  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    let active = true, timer;
    const controller = new AbortController();
    async function poll() {
      let nextPollMs = intervalMs;
      try {
        const next = await api(path, { signal: controller.signal, timeoutMs });
        if (active) { setData(next); setError(null); }
      } catch (e) {
        if (active && e.name !== "AbortError") setError(e);
        // Refreshing media links is infrequent; recovering a failed read isn't.
        nextPollMs = Math.min(intervalMs, 2000);
      } finally {
        if (active) {
          setLoaded(true);
          if (intervalMs) timer = setTimeout(poll, nextPollMs);
        }
      }
    }
    poll();
    return () => { active = false; controller.abort(); clearTimeout(timer); };
  }, [path, intervalMs, timeoutMs, revision]);

  return { data, error, loaded, refresh };
}

function Stepper({ step, labels }) {
  return (
    <ol className="stepper">
      {labels.map((name, i) => {
        const n = i + 1;
        const state = n < step ? "done" : n === step ? "now" : "next";
        return (
          <li key={name} className={`step step-${state}`}>
            <span className="step-dot">{n < step ? "✓" : n}</span>
            <span className="step-name">{name}</span>
          </li>
        );
      })}
    </ol>
  );
}

function State({ title, children }) {
  return (
    <div className="state">
      <strong>{title}</strong>
      <span className="muted">{children}</span>
    </div>
  );
}

function NewJob({ onQueued }) {
  const t = useCopy().work;
  const [step, setStep] = useState(1);
  const [kind, setKind] = useState(null);
  const [value, setValue] = useState("");
  const [provider, setProvider] = useState("codex");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [queued, setQueued] = useState(null);

  const field = kind ? FIELDS[kind] : null;
  const copy = kind ? t.pipelines[kind] : null;

  function choose(next) {
    setKind(next);
    setValue("");
    setError(null);
    setStep(2);
  }

  function toReview(event) {
    event.preventDefault();
    if (value.trim()) setStep(3);
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const { id } = await api("/jobs", {
        method: "POST",
        body: JSON.stringify({ kind, [field.key]: value.trim(), llm_provider: provider }),
      });
      setQueued(id);
      setStep(4);
      onQueued?.();
    } catch (e) {
      setError(e);
      // Back to the input: a rejected payload is almost always the input.
      setStep(2);
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setStep(1);
    setKind(null);
    setValue("");
    setQueued(null);
    setError(null);
  }

  if (step === 4) {
    return (
      <div className="panel panel-narrow">
        <span className="panel-label">{t.queuedLabel}</span>
        <div className="panel-body">
          <h3 className="done-head">{t.queuedTitle}</h3>
          <p className="muted" style={{ marginTop: 10 }}>
            <code>{queued}</code> {t.queuedBody}
          </p>
          <div className="hero-actions" style={{ marginTop: 24 }}>
            <button className="btn btn-primary" onClick={reset}>
              {t.queuedAgain}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="panel panel-narrow">
      <span className="panel-label">{t.tabs.new}</span>
      <div className="panel-body">
        <Stepper step={step} labels={t.steps} />

        {error && <p className="alarm-text form-error">{userError(error, t.errors)}</p>}

        {step === 1 && (
          <div className="choice-grid">
            {Object.entries(FIELDS).map(([id, spec]) => (
              <button type="button" className="choice" key={id} onClick={() => choose(id)}>
                <span className={`kind-tag kind-${id}`}>{spec.code}</span>
                <b>{t.pipelines[id].name}</b>
                <span className="choice-tagline">{t.pipelines[id].tagline}</span>
                <small>{t.pipelines[id].blurb}</small>
              </button>
            ))}
            <p className="muted choice-note">{t.note}</p>
          </div>
        )}

        {step === 2 && field && (
          <form onSubmit={toReview}>
            <label>
              <span className="label">{copy.field}</span>
              <input
                required
                autoFocus
                value={value}
                type={field.type}
                placeholder={field.placeholder}
                onChange={(e) => setValue(e.target.value)}
              />
            </label>
            <p className="muted" style={{ margin: 0, fontSize: 13 }}>
              {copy.hint}
            </p>
            <label htmlFor="generation-provider">
              <span id="generation-provider-label" className="label">{t.model.label}</span>
              <select id="generation-provider" value={provider}
                aria-labelledby="generation-provider-label"
                aria-describedby="generation-provider-hint"
                onChange={(event) => setProvider(event.target.value)}>
                {Object.entries(GENERATION_PROVIDERS).map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </select>
              <small id="generation-provider-hint" className="muted">{t.model.hint}</small>
            </label>
            <div className="hero-actions">
              <button type="button" className="btn" onClick={() => setStep(1)}>
                {t.back}
              </button>
              <button className="btn btn-primary" disabled={!value.trim()}>
                {t.review}
              </button>
            </div>
          </form>
        )}

        {step === 3 && field && (
          <div>
            <dl className="review">
              <div>
                <dt className="label">{t.steps[0]}</dt>
                <dd>
                  <span className={`kind-tag kind-${kind}`}>{field.code}</span> {copy.name}
                </dd>
              </div>
              <div>
                <dt className="label">{copy.field}</dt>
                <dd className="review-value">{value}</dd>
              </div>
              <div>
                <dt className="label">{t.model.label}</dt>
                <dd>{GENERATION_PROVIDERS[provider]}</dd>
              </div>
            </dl>
            <p className="muted" style={{ fontSize: 13 }}>
              {t.reviewWarn}
            </p>
            <div className="hero-actions">
              <button className="btn" onClick={() => setStep(2)} disabled={busy}>
                {t.edit}
              </button>
              <button className="btn btn-primary" onClick={submit} disabled={busy}>
                {busy ? t.queueing : t.queueIt}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function inputOf(job) {
  return job.params?.topic || job.params?.youtube_url || job.params?.title || "—";
}

function DeleteDialog({ job, busy, error, onConfirm, onCancel }) {
  const work = useCopy().work;
  const t = work.remove;
  const dialog = useRef(null);
  useEffect(() => { dialog.current.showModal(); }, []);
  return (
    <dialog ref={dialog} className="delete-dialog" aria-labelledby="delete-title"
      onCancel={(event) => { event.preventDefault(); if (!busy) onCancel(); }}>
      <h2 id="delete-title">{job.status === "running" ? t.runningTitle : t.title}</h2>
      <p className="delete-input">{inputOf(job)}</p>
      <p>{t.confirm}</p>
      {job.status === "running" && <p>{t.running}</p>}
      {error && <p role="alert" className="alarm-text">{userError(error, work.errors)}</p>}
      <div className="queue-actions">
        <button className="btn" disabled={busy} onClick={onCancel} autoFocus>{t.cancel}</button>
        <button className="btn btn-primary" disabled={busy} onClick={onConfirm}>{busy ? t.busy : t.confirmButton}</button>
      </div>
    </dialog>
  );
}

function Queue() {
  const t = useCopy().work;
  const { data, error, loaded, refresh } = usePoll("/jobs", 2000);
  const [selected, setSelected] = useState(null);
  const [confirming, setConfirming] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [deleteError, setDeleteError] = useState(null);
  const [retrying, setRetrying] = useState(null);
  const [retryError, setRetryError] = useState(null);
  const [retried, setRetried] = useState(null);
  const [inspectionVersion, setInspectionVersion] = useState(0);

  async function retry(jobId) {
    setRetrying(jobId);
    setRetryError(null);
    setRetried(null);
    try {
      await api("/jobs/" + jobId + "/retry", { method: "POST" });
      setRetried(jobId);
      if (selected === jobId) setInspectionVersion((value) => value + 1);
      refresh();
    } catch (e) {
      setRetryError(e);
      refresh();
    } finally {
      setRetrying(null);
    }
  }

  async function remove(jobId) {
    setDeleting(jobId);
    setDeleteError(null);
    try {
      await api("/jobs/" + jobId, { method: "DELETE" });
      if (selected === jobId) setSelected(null);
      setConfirming(null);
      refresh();
    } catch (e) {
      setDeleteError(e);
      refresh();
    } finally {
      setDeleting(null);
    }
  }

  if (error && !data.length) return <State title={t.unreachable}>{userError(error, t.errors)}</State>;
  if (!loaded) return <State title={t.reading}>{t.readingQueue}</State>;
  if (!data.length) return <State title={t.emptyQueue}>{t.emptyQueueBody}</State>;

  const counts = data.reduce((acc, job) => {
    acc[job.status] = (acc[job.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <>
      {error && <p role="status" className="alarm-text">{t.execution.stale} {userError(error, t.errors)}</p>}
      {retryError && <p role="alert" className="alarm-text">{userError(retryError, t.errors, "retry")}</p>}
      {retried && data.some((job) => job.id === retried && ["pending", "running"].includes(job.status)) &&
        <p role="status" className="muted">{t.retry.queued}</p>}
      <div className="count-row">
        {Object.entries(counts).map(([status, n]) => (
          <span className={`status status-${status}`} key={status}>
            {n} {status}
          </span>
        ))}
      </div>

      <div className="panel">
        <span className="panel-label">
          {t.jobsLabel} · {data.length}
        </span>
        <div className="panel-body">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t.colPipeline}</th>
                  <th>{t.colInput}</th>
                  <th>{t.colStatus}</th>
                  <th>{t.execution.stage}</th>
                  <th>{t.execution.attempt}</th>
                  <th>{t.execution.elapsed}</th>
                  <th>{t.colQueued}</th>
                </tr>
              </thead>
              <tbody>
                {data.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <span className={`kind-tag kind-${job.kind}`}>{job.kind}</span>
                    </td>
                    <td>
                      {inputOf(job)}
                      {GENERATION_PROVIDERS[job.params?.llm_provider] && (
                        <small className="execution-scope">{GENERATION_PROVIDERS[job.params.llm_provider]}</small>
                      )}
                      {(job.error || job.error_summary) && <p className="job-error">{userError(job.error || job.error_summary, t.errors)}</p>}
                      <div className="job-actions" role="group" aria-label={t.actions}>
                        <button className="btn" aria-expanded={selected === job.id}
                          aria-controls={selected === job.id ? "execution-" + job.id : undefined}
                          onClick={() => setSelected(selected === job.id ? null : job.id)}>
                          {selected === job.id ? t.execution.close : t.execution.inspect}
                        </button>
                        {job.status === "failed" && <button className="btn" disabled={!!deleting || !!retrying}
                          onClick={() => retry(job.id)}>{retrying === job.id ? t.retry.busy : t.retry.label}</button>}
                        <button className="btn" disabled={!!deleting || !!retrying}
                          onClick={() => { setConfirming(job); setDeleteError(null); }}>{t.remove.label}</button>
                      </div>
                    </td>
                    <td>
                      <span className={`status status-${job.status}`}>{job.status}</span>
                    </td>
                    <td>{job.current_stage ? (t.execution.names[job.current_stage.stage] || job.current_stage.stage) : "—"}</td>
                    <td className="numeric">{job.attempts ?? 0} / {job.max_attempts ?? 3}</td>
                    <td className="numeric">{duration(job.duration_seconds)}</td>
                    <td className="muted" style={{ fontSize: 13 }}>
                      {new Date(job.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      {selected && <Execution key={selected + ":" + inspectionVersion} jobId={selected} />}
      {confirming && <DeleteDialog job={confirming} busy={!!deleting} error={deleteError}
        onConfirm={() => remove(confirming.id)} onCancel={() => setConfirming(null)} />}
    </>
  );
}

function Output() {
  const t = useCopy().work;
  // Signed URLs expire in an hour, so refresh well inside that window.
  // Media-link signing can take longer than queue reads on a cold connection.
  const { data, error, loaded } = usePoll("/gallery", 15 * 60 * 1000, 45000);

  if (error && !data.length) return <State title={t.unreachable}>{userError(error, t.errors)}</State>;
  if (!loaded) return <State title={t.reading}>{t.readingOutput}</State>;
  if (!data.length) return <State title={t.emptyOutput}>{t.emptyOutputBody}</State>;

  return (
    <>
    {error && <p role="status" className="alarm-text">{t.execution.stale} {userError(error, t.errors)}</p>}
    <div className="gallery">
      {data.map((item) => (
        <figure key={`${item.source}-${item.id}`}>
          <video src={item.url} controls preload="metadata" />
          <figcaption>
            {item.title}
            <br />
            <span className="label">{item.source}</span>
          </figcaption>
        </figure>
      ))}
    </div>
    </>
  );
}

const SCREENS = { new: NewJob, queue: Queue, output: Output };

export default function Workspace() {
  const t = useCopy().work;
  const [tab, setTab] = useState("new");
  const Screen = SCREENS[tab];

  return (
    <div className="page">
      <header className="page-head">
        <span className="label">{t.label}</span>
        <h1>{t.headings[tab]}</h1>
      </header>

      <div className="segmented">
        {Object.keys(SCREENS).map((id) => (
          <button key={id} aria-current={id === tab} onClick={() => setTab(id)}>
            {t.tabs[id]}
          </button>
        ))}
      </div>

      <Screen onQueued={() => setTab("queue")} />
    </div>
  );
}
