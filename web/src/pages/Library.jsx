import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { useLang } from "../i18n.jsx";
import { INTEGRATIONS_COPY } from "../integrations-copy.js";

export default function Library() {
  const { lang } = useLang(); const t = INTEGRATIONS_COPY[lang];
  const [query, setQuery] = useState(""); const [provider, setProvider] = useState("nasa");
  const [rows, setRows] = useState(null); const [saved, setSaved] = useState([]); const [active, setActive] = useState([]);
  const [busy, setBusy] = useState(""); const [error, setError] = useState("");
  async function refresh() { setSaved(await api("/library")); }
  useEffect(() => { refresh().catch(() => setError(t.error)); }, []);
  async function search(event) {
    event.preventDefault(); setBusy("search"); setError("");
    try { setRows(await api(`/library/search?provider=${provider}&q=${encodeURIComponent(query)}`)); }
    catch (e) { setError(e.status === 422 ? e.message : t.error); } finally { setBusy(""); }
  }
  async function act(row, activate = false) {
    const key = row.provider + "/" + row.id; setBusy(key); setError("");
    try {
      await api("/library/" + key + (activate ? "/activate" : ""), { method: "POST", timeoutMs: 180000 });
      if (activate) setActive((previous) => [...previous, key]);
      await refresh();
    } catch (e) { setError([404, 422].includes(e.status) ? e.message : t.error); } finally { setBusy(""); }
  }
  return <section><p className="muted">{t.mediaIntro}</p><p className="muted">{t.portable}</p>
    <form onSubmit={search}><div className="insights-fields">
      <label><span className="label">{t.provider}</span><select aria-label={t.provider} value={provider} onChange={(e) => setProvider(e.target.value)}>
        <option value="nasa">NASA</option><option value="pexels">Pexels</option></select></label>
      <label><span className="label">{t.query}</span><input required minLength={2} maxLength={120} value={query} onChange={(e) => setQuery(e.target.value)} /></label></div>
      <button className="btn btn-primary" disabled={!!busy}>{busy === "search" ? t.searching : t.search}</button></form>
    <p><a href="https://www.pexels.com" target="_blank" rel="noreferrer">{t.pexelsCredit}</a> · {t.nasaCredit}</p>
    {error && <p role="alert" className="alarm-text">{error}</p>}
    <div className="media-search-results">{rows?.map((row) => <article className="panel" key={row.provider + row.id}><div className="panel-body">
      {row.preview && <img src={row.preview} alt="" loading="lazy" />}<h2 className="retention-heading">{row.title}</h2>
      <p>{row.credit}</p><a href={row.source_url} target="_blank" rel="noreferrer">{t.source}</a>
      <div className="job-actions"><button className="btn" disabled={!!busy || saved.some((item) => item.id === row.id && item.provider === row.provider)} onClick={() => act(row)}>
        {busy === row.provider + "/" + row.id ? t.saving : t.save}</button></div>
    </div></article>)}</div>
    {rows?.length === 0 && <p>{t.noResults}</p>}
    <h2 className="retention-heading">{t.downloads}</h2><div className="gallery">{saved.map((row) => <figure key={row.storage_path}>
      <video src={row.url} controls preload="none" /><figcaption><b>{row.title}</b><p>{row.credit}</p>
        {row.source_url && <a href={row.source_url} target="_blank" rel="noreferrer">{t.source}</a>}{row.license_url && <> · <a href={row.license_url} target="_blank" rel="noreferrer">{t.license}</a></>}
        {row.provider !== "existing" ? <div className="job-actions"><button className="btn" disabled={!!busy || row.active || active.includes(row.provider + "/" + row.id)} onClick={() => act(row, true)}>
          {row.active || active.includes(row.provider + "/" + row.id) ? t.active : t.activate}</button></div> : row.active && <p className="label">{t.active}</p>}</figcaption>
    </figure>)}</div>
  </section>;
}
