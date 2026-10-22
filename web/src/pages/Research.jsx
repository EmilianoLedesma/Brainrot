import React, { useState } from "react";
import { api } from "../api.js";
import { useLang } from "../i18n.jsx";
import { INTEGRATIONS_COPY } from "../integrations-copy.js";

export default function Research({ onReference }) {
  const { lang } = useLang(); const t = INTEGRATIONS_COPY[lang];
  const [query, setQuery] = useState(""); const [rows, setRows] = useState(null);
  const [selected, setSelected] = useState(null); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  async function search(event) {
    event.preventDefault(); setBusy(true); setError(""); setSelected(null);
    try { setRows(await api("/research/search?q=" + encodeURIComponent(query))); } catch { setError(t.error); } finally { setBusy(false); }
  }
  async function inspect(id) {
    setBusy(true); setError("");
    try { setSelected(await api("/research/" + id)); } catch { setError(t.error); } finally { setBusy(false); }
  }
  return <section><p className="muted">{t.researchIntro}</p>
    <form onSubmit={search}><label><span className="label">{t.query}</span><input required minLength={2} maxLength={120} value={query} onChange={(e) => setQuery(e.target.value)} /></label>
      <button className="btn btn-primary" disabled={busy}>{busy ? t.searching : t.search}</button></form>
    {error && <p className="alarm-text" role="alert">{error}</p>}
    <div className="reference-results">{rows?.map((row) => <button className="choice" key={row.id} disabled={busy} onClick={() => inspect(row.id)}>
      <b>{row.label}</b><small>{row.description}</small><span className="muted">{row.id}</span></button>)}</div>
    {rows?.length === 0 && <p>{t.noResults}</p>}
    {selected && <div className="panel"><span className="panel-label">{t.facts}</span><div className="panel-body">
      <h2 className="retention-heading">{selected.label}</h2><p>{selected.description}</p>
      <a href={selected.url} target="_blank" rel="noreferrer">Wikidata · {selected.id}</a>
      <dl className="reference-facts">{selected.facts.map((fact, index) => <div key={index}><dt>{fact.property}</dt><dd>{fact.value}
        {fact.sources.length ? fact.sources.map((url) => <a className="execution-scope" key={url} href={url} target="_blank" rel="noreferrer">{t.source}</a>) : <small className="execution-scope">{t.unsourced}</small>}</dd></div>)}</dl>
      <button className="btn btn-primary" onClick={() => onReference(selected)}>{t.choose}</button>
    </div></div>}
  </section>;
}
