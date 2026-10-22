import React, { useRef, useState } from "react";
import { api } from "../api.js";
import { useLang } from "../i18n.jsx";
import { INSIGHTS_COPY } from "../insights-copy.js";

export function newInsightsSession() {
  return { csv: "", csvName: "", srt: "", srtName: "", duration: "", axis: "", unit: "", timeColumn: 1, retentionColumn: 2, report: null, step: 1 };
}

const number = (value) => Number(value.toFixed(2));

function Curve({ report, copy }) {
  const [selected, setSelected] = useState(0);
  const maxY = Math.max(100, ...report.points.map((point) => point.retention));
  const x = (seconds) => 60 + seconds / report.duration_seconds * 710;
  const y = (retention) => 240 - retention / maxY * 210;
  const point = report.points[Math.min(selected, report.points.length - 1)];
  return <div className="retention-curve">
    <svg viewBox="0 0 800 290" role="img" aria-label={copy.chart}>
      <title>{copy.chart}</title>
      {[0, 0.5, 1].map((fraction) => <g key={fraction}>
        <line x1="60" x2="770" y1={y(fraction * maxY)} y2={y(fraction * maxY)} className="retention-grid" />
        <text x="50" y={y(fraction * maxY) + 4} textAnchor="end">{number(fraction * maxY)}%</text>
        <text x={x(fraction * report.duration_seconds)} y="263" textAnchor="middle">{number(fraction * report.duration_seconds)}s</text>
      </g>)}
      {report.drops.map((drop) => <rect key={drop.start_seconds} x={x(drop.start_seconds)} y="30"
        width={Math.max(1, x(drop.end_seconds) - x(drop.start_seconds))} height="210" className="retention-drop" />)}
      <polyline points={report.points.map((p) => `${x(p.seconds)},${y(p.retention)}`).join(" ")} className="retention-line" />
      <circle cx={x(point.seconds)} cy={y(point.retention)} r="6" className="retention-cursor" />
    </svg>
    <label>
      <span className="label">{copy.time}: {number(point.seconds)} · {number(point.retention)}%</span>
      <input type="range" aria-label={copy.chart} min="0" max={report.points.length - 1} step="1"
        value={selected} onChange={(event) => setSelected(Number(event.target.value))}
        aria-valuetext={`${number(point.seconds)}s, ${number(point.retention)}%`} />
    </label>
    <small className="muted">{copy.audience}</small>
  </div>;
}

export default function Insights({ insightSession: session, onInsightSessionChange: setSession }) {
  const { lang } = useLang();
  const t = INSIGHTS_COPY[lang];
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const reads = useRef({ csv: 0, srt: 0 });
  const update = (key, value) => { setSession((previous) => ({ ...previous, [key]: value })); setError(""); };

  async function readFile(event, kind) {
    const file = event.target.files[0];
    const request = ++reads.current[kind];
    update(kind, "");
    update(kind + "Name", "");
    if (!file) return;
    if (file.size > 250_000) { setError(t.size); event.target.value = ""; return; }
    try {
      const text = await file.text();
      if (request !== reads.current[kind]) return;
      setSession((previous) => ({ ...previous, [kind]: text, [kind + "Name"]: file.name }));
    } catch { setError(t.readError); }
  }

  async function analyze(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const report = await api("/insights/retention", { method: "POST", body: JSON.stringify({
        csv_text: session.csv, axis: session.axis, retention_unit: session.unit,
        duration_seconds: Number(session.duration), transcript_srt: session.srt,
        time_column: Number(session.timeColumn) - 1, retention_column: Number(session.retentionColumn) - 1,
      }) });
      setSession((previous) => ({ ...previous, report, step: 2 }));
    } catch (exception) {
      setError(exception.status === 422 && !exception.message.includes("[object") ? exception.message : t.error);
    } finally { setBusy(false); }
  }

  function download() {
    const blob = new Blob([JSON.stringify({ source_file: session.csvName, ...session.report }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "brainrot-retention-report.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const report = session.report;
  return <section className="insights" aria-label={t.chart}>
    <p className="muted">{t.intro}</p>
    <div className="stepper" aria-label={t.import}>
      {[t.import, t.report].map((label, index) => <div className={`step ${session.step === index + 1 ? "step-now" : session.step > index + 1 ? "step-done" : ""}`} key={label}>
        <span className="step-dot">{index + 1}</span><span className="step-name">{label}</span>
      </div>)}
    </div>
    {error && <p role="alert" className="alarm-text">{error}</p>}
    {session.step === 1 && <div className="panel panel-narrow">
      <span className="panel-label">{t.import}</span>
      <div className="panel-body"><form onSubmit={analyze}>
        <label><span className="label">{t.csv}</span><input type="file" accept=".csv,.tsv,text/csv,text/tab-separated-values" disabled={busy}
          onChange={(event) => readFile(event, "csv")} /><small className="muted">{session.csvName || t.format}</small></label>
        <label><span className="label">{t.duration}</span><input required type="number" min="1" max="86400" step="0.01" value={session.duration}
          disabled={busy} onChange={(event) => update("duration", event.target.value)} /><small className="muted">{t.durationHint}</small></label>
        <div className="insights-fields">
          <label><span className="label">{t.axis}</span><select required aria-label={t.axis} value={session.axis} disabled={busy} onChange={(event) => update("axis", event.target.value)}>
            <option value="">{t.choose}</option>{["seconds", "percent", "fraction"].map((unit) => <option value={unit} key={unit}>{t[unit]}</option>)}</select></label>
          <label><span className="label">{t.retention}</span><select required aria-label={t.retention} value={session.unit} disabled={busy} onChange={(event) => update("unit", event.target.value)}>
            <option value="">{t.choose}</option>{["percent", "fraction"].map((unit) => <option value={unit} key={unit}>{t[unit]}</option>)}</select></label>
        </div>
        <details><summary>{t.columns}</summary><p className="muted">{t.columnsHint}</p><div className="insights-fields">
          <label><span className="label">{t.timeColumn}</span><input type="number" required min="1" max="100" step="1" disabled={busy}
            value={session.timeColumn} onChange={(event) => update("timeColumn", event.target.value)} /></label>
          <label><span className="label">{t.retentionColumn}</span><input type="number" required min="1" max="100" step="1" disabled={busy}
            value={session.retentionColumn} onChange={(event) => update("retentionColumn", event.target.value)} /></label>
        </div></details>
        <label><span className="label">{t.srt}</span><input type="file" accept=".srt" disabled={busy} onChange={(event) => readFile(event, "srt")} />
          <small className="muted">{session.srtName || t.optional}</small></label>
        {session.srt && <button type="button" className="btn" disabled={busy} onClick={() => { update("srt", ""); update("srtName", ""); }}>{t.clear}</button>}
        <button type="submit" className="btn btn-primary" disabled={busy || !session.csv}>{busy ? t.analyzing : t.analyze}</button>
      </form></div>
    </div>}
    {session.step === 2 && report && <div className="panel">
      <span className="panel-label">{t.report}</span>
      <div className="panel-body">
        <div className="queue-pagination"><strong>{session.csvName}</strong><div className="queue-actions">
          <button className="btn" onClick={() => update("step", 1)}>{t.edit}</button>
          <button className="btn" onClick={download}>{t.download}</button>
        </div></div>
        <dl className="retention-facts">
          <div><dt>{t.opening} · {report.opening_seconds}s</dt><dd>{number(-report.opening_loss_pp)} pp</dd></div>
          <div><dt>{t.last} · {number(report.last_observed_seconds)}s</dt><dd>{number(report.last_observed_retention)}%</dd></div>
          <div><dt>{t.samples}</dt><dd>{report.points.length}</dd></div>
        </dl>
        <Curve report={report} copy={t} />
        <p className="muted">{t.units}</p>
        <h2 className="retention-heading">{t.drops}</h2>
        {report.drops.length ? <div className="table-wrap"><table>
          <thead><tr><th>{t.interval}</th><th>{t.loss}</th><th>{t.rate}</th><th>{t.excerpt}</th></tr></thead>
          <tbody>{report.drops.map((drop) => <tr key={drop.start_seconds}>
            <td className="numeric">{number(drop.start_seconds)}–{number(drop.end_seconds)}s</td>
            <td>{number(drop.loss_pp)} pp</td><td>{drop.rate_pp_per_second} pp/s</td>
            <td>{drop.excerpt || <span className="muted">{t.noExcerpt}</span>}</td>
          </tr>)}</tbody>
        </table></div> : <p>{t.noDrops}</p>}
        <p>{t.note}</p><h3 className="retention-heading">{t.review}</h3><p>{t.reviewBody}</p>
        <small className="muted">{t.pending}</small>
      </div>
    </div>}
  </section>;
}
