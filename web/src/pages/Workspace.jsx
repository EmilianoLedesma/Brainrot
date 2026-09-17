import React, { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { useCopy } from "../i18n.jsx";

/* The work surface. Submitting a job is a three-step flow rather than one form,
   because picking a pipeline and describing the input are different decisions and
   the review step is the last chance to catch a wrong paste.

   Pipeline ids, field keys and placeholders are backend contract, so they live
   here rather than in the translation tree. */

const FIELDS = {
  brainrot: { code: "H2", key: "topic", type: "text", placeholder: "roman empire silver crisis" },
  repurpose: { code: "H1", key: "youtube_url", type: "url", placeholder: "https://youtube.com/watch?v=..." },
};

function usePoll(path, intervalMs) {
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(() => {
    api(path).then(
      (d) => {
        setData(d);
        setError(null);
        setLoaded(true);
      },
      (e) => {
        setError(e.message);
        setLoaded(true);
      },
    );
  }, [path]);

  useEffect(() => {
    refresh();
    if (!intervalMs) return;
    const id = setInterval(refresh, intervalMs);
    return () => clearInterval(id);
  }, [refresh, intervalMs]);

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
        body: JSON.stringify({ kind, [field.key]: value.trim() }),
      });
      setQueued(id);
      setStep(4);
      onQueued?.();
    } catch (e) {
      setError(e.message);
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

        {error && <p className="alarm-text form-error">{error}</p>}

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
  return job.params?.topic || job.params?.youtube_url || "—";
}

function Queue() {
  const t = useCopy().work;
  const { data, error, loaded } = usePoll("/jobs", 2000);

  if (error) return <State title={t.unreachable}>{error}</State>;
  if (!loaded) return <State title={t.reading}>{t.readingQueue}</State>;
  if (!data.length) return <State title={t.emptyQueue}>{t.emptyQueueBody}</State>;

  const counts = data.reduce((acc, job) => {
    acc[job.status] = (acc[job.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <>
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
                      {job.error && <pre className="trace">{job.error}</pre>}
                    </td>
                    <td>
                      <span className={`status status-${job.status}`}>{job.status}</span>
                    </td>
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
    </>
  );
}

function Output() {
  const t = useCopy().work;
  // Signed URLs expire in an hour, so refresh well inside that window.
  const { data, error, loaded } = usePoll("/gallery", 15 * 60 * 1000);

  if (error) return <State title={t.unreachable}>{error}</State>;
  if (!loaded) return <State title={t.reading}>{t.readingOutput}</State>;
  if (!data.length) return <State title={t.emptyOutput}>{t.emptyOutputBody}</State>;

  return (
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
