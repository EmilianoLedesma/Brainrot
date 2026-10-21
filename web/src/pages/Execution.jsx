import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { useCopy } from "../i18n.jsx";
import { GENERATION_PROVIDERS, brainrotSummary } from "../generation.js";
import { userError } from "../errors.js";

export function duration(value) {
  if (value == null) return "—";
  return value < 60 ? Number(value).toFixed(1) + "s" : Math.floor(value / 60) + "m " + Math.floor(value % 60) + "s";
}

export default function Execution({ jobId }) {
  const work = useCopy().work;
  const t = work.execution;
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    let active = true, timer;
    const controller = new AbortController();
    async function poll() {
      try {
        const next = await api("/jobs/" + jobId, { signal: controller.signal });
        if (active) { setData(next); setError(null); }
      } catch (e) {
        if (active && e.name !== "AbortError") setError(e);
      } finally {
        if (active) timer = setTimeout(poll, 2000);
      }
    }
    poll();
    return () => { active = false; controller.abort(); clearTimeout(timer); };
  }, [jobId]);
  if (!data) return <div className="state" role="status">{error ? userError(error, work.errors) : t.loading}</div>;
  const { job, publications } = data;
  // A queued retry still has the previous attempt number until it is claimed.
  // Keep that attempt's rows out of the new run's view as well.
  const stages = job.status === "pending" ? [] : data.stages.filter((stage) => stage.attempt === job.attempts);
  const stamp = (value) => value ? new Date(value).toLocaleString() : "—";
  return (
    <section className="panel execution-panel" id={"execution-" + jobId} aria-label={t.title}>
      <span className="panel-label">{t.title} · {job.kind}</span>
      <div className="panel-body">
        {error && <p role="status" className="alarm-text">{t.stale} {userError(error, work.errors)}</p>}
        <div className="execution-heading">
          <code>{job.id}</code>
          <span className={"status status-" + job.status}>{job.status}</span>
        </div>
        <p className="muted">{work.model.label}: <b>{GENERATION_PROVIDERS[job.params?.llm_provider] || work.model.workerDefault}</b></p>
        {Number.isInteger(job.params?.brainrot_level) && <p className="muted">
          {work.brainrot.label}: <b>{brainrotSummary(job.params.brainrot_level, work.brainrot)}</b>
        </p>}
        <dl className="execution-facts">
          <div><dt>{t.attempt}</dt><dd>{job.attempts ?? 0} / {job.max_attempts ?? 3}</dd></div>
          <div><dt>{t.started}</dt><dd>{stamp(job.started_at)}</dd></div>
          <div><dt>{t.finished}</dt><dd>{stamp(job.finished_at)}</dd></div>
          <div><dt>{t.retryAt}</dt><dd>{job.status === "pending" && job.attempts > 0 ? stamp(job.run_after) : "—"}</dd></div>
        </dl>
        {(job.error_summary || job.error) && <p className="execution-error" role="status">{userError(job.error_summary || job.error, work.errors)}</p>}
        <h3 className="execution-subhead">{t.stages}</h3>
        {stages.length ? <div className="table-wrap"><table aria-label={t.stages}>
          <thead><tr><th>{t.stage}</th><th>{t.attempt}</th><th>{t.status}</th><th>{t.elapsed}</th><th>{t.started}</th></tr></thead>
          <tbody>{stages.map((stage) => <tr key={stage.id}>
            <td><b>{t.names[stage.stage] || stage.stage}</b>{stage.scope && <small className="execution-scope">{stage.scope}</small>}
              {stage.error && <p className="job-error">{userError(stage.error, work.errors, stage.stage)}</p>}</td>
            <td>{stage.attempt}</td><td><span className={"status status-" + stage.status}>{stage.status}</span></td>
            <td className="numeric">{duration(stage.duration_seconds ?? (stage.status === "running" ? Math.max(0, (Date.now() - Date.parse(stage.started_at)) / 1000) : null))}</td>
            <td className="muted">{stamp(stage.started_at)}</td>
          </tr>)}</tbody>
        </table></div> : <p className="muted">{t.noStages}</p>}
        <h3 className="execution-subhead">{t.publications}</h3>
        {publications.length ? <div className="table-wrap"><table>
          <thead><tr><th>{t.platform}</th><th>{t.status}</th><th>{t.scheduled}</th><th>{t.published}</th></tr></thead>
          <tbody>{publications.map((publication) => <tr key={publication.id}>
            <td>{publication.platform}</td><td><span className={"status status-" + publication.status}>{publication.status}</span>
              {publication.error && <p className="job-error">{userError(publication.error, work.errors, "publish")}</p>}</td>
            <td>{stamp(publication.scheduled_at)}</td><td>{stamp(publication.published_at)}</td>
          </tr>)}</tbody>
        </table></div> : <p className="muted">{t.noPublications}</p>}
      </div>
    </section>
  );
}
