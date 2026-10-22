import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { useLang } from "../i18n.jsx";
import { INTEGRATIONS_COPY } from "../integrations-copy.js";

function today(offset = 0) { const date = new Date(); date.setDate(date.getDate() + offset); return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`; }

export default function YouTube({ onRetention }) {
  const { lang } = useLang(); const t = INTEGRATIONS_COPY[lang];
  const [connection, setConnection] = useState(null); const [output, setOutput] = useState([]); const [uploads, setUploads] = useState([]);
  const [step, setStep] = useState(1); const [selected, setSelected] = useState(null);
  const [title, setTitle] = useState(""); const [description, setDescription] = useState(""); const [privacy, setPrivacy] = useState("private"); const [tags, setTags] = useState("");
  const [kids, setKids] = useState(false); const [synthetic, setSynthetic] = useState(false);
  const [busy, setBusy] = useState(""); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  const [authUrl, setAuthUrl] = useState(""); const [videos, setVideos] = useState(null); const [videoId, setVideoId] = useState("");
  const [start, setStart] = useState(today(-28)); const [end, setEnd] = useState(today());
  const [performance, setPerformance] = useState([]);
  const [autoPublish, setAutoPublish] = useState(false); const [autoPrivacy, setAutoPrivacy] = useState("private"); const [includeQueued, setIncludeQueued] = useState(false);
  async function refresh() {
    const [status, rows] = await Promise.all([api("/youtube/status"), api("/youtube/uploads")]);
    setConnection(status); setUploads(rows);
    setAutoPublish(status.auto_publish || false); setAutoPrivacy(status.privacy_status || "private");
    if (status.connected) { setOutput(await api("/gallery", { timeoutMs: 45000 })); setPerformance(await api("/youtube/performance")); }
  }
  useEffect(() => { refresh().catch(() => setError(t.error)); }, []);
  useEffect(() => {
    if (!uploads.some((row) => row.status === "uploading")) return;
    const timer = setInterval(() => { api("/youtube/uploads").then(setUploads).catch(() => setError(t.error)); }, 3000);
    return () => clearInterval(timer);
  }, [uploads]);
  async function action(name, work) {
    setBusy(name); setError(""); setMessage("");
    try { await work(); } catch (e) { setError([409, 422].includes(e.status) && !e.message.includes("[object") ? e.message : t.error); }
    finally { setBusy(""); }
  }
  async function generateDetails(item, regenerate = false) {
    await action("metadata", async () => {
      const result = await api("/youtube/metadata", { method: "POST", timeoutMs: 240000,
        body: JSON.stringify({ source: item.source, target_id: item.id, regenerate }) });
      setTitle(result.title); setDescription(result.description); setTags(result.tags.join(", "));
    });
  }
  function choose(item) { setSelected(item); setTitle(item.title.slice(0, 100)); setDescription(""); setPrivacy(item.youtube?.privacy_status || "private"); setTags(""); setKids(item.youtube?.made_for_kids || false); setSynthetic(item.youtube?.contains_synthetic_media || false); setStep(2); setMessage(""); generateDetails(item); }
  async function upload() {
    await action("upload", async () => {
      await api("/youtube/upload", { method: "POST", body: JSON.stringify({ source: selected.source, target_id: selected.id,
        title, description, privacy_status: privacy, tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
        made_for_kids: kids, contains_synthetic_media: synthetic }) });
      setMessage(t.uploadStarted); setStep(1); setSelected(null); await refresh();
    });
  }
  return <section><p className="muted">{t.youtubeIntro}</p>
    {error && <p role="alert" className="alarm-text">{error}</p>}{message && <p role="status">{message}</p>}
    <div className="panel"><span className="panel-label">{t.youtube}</span><div className="panel-body">
      <p><strong>{connection?.connected ? `${t.connected}: ${connection.channel_title || connection.channel_id || "YouTube"}` : connection?.configured ? t.configured : t.missing}</strong></p>
      <div className="job-actions"><button className="btn" disabled={!!busy} onClick={() => action("refresh", refresh)}>{t.refresh}</button>
        {connection?.connected ? <button className="btn" disabled={!!busy || uploads.some((row) => row.status === "uploading")} onClick={() => action("disconnect", async () => { await api("/youtube/connection", { method: "DELETE" }); setOutput([]); setVideos(null); await refresh(); })}>{t.disconnect}</button>
          : <button className="btn btn-primary" disabled={!!busy || !connection?.configured} onClick={() => action("connect", async () => { const response = await api("/youtube/connect", { method: "POST" }); setAuthUrl(response.url); })}>{t.connect}</button>}
        {authUrl && !connection?.connected && <a className="btn" href={authUrl} target="_blank" rel="noreferrer">{t.connecting}</a>}</div>
      {authUrl && !connection?.connected && <p>{t.waiting}</p>}
      {!connection?.connected && <details open={!connection?.configured}><summary>{t.setup}</summary><p>{t.setupLead}</p>
        <ol>{t.setupSteps.map((text, index) => <li key={text}>{text}{index === 2 && <pre className="redirect-uri">{connection?.redirect_uri || "http://127.0.0.1:8001/youtube/callback"}</pre>}</li>)}</ol>
        <a href="https://console.cloud.google.com/apis/dashboard" target="_blank" rel="noreferrer">{t.cloud}</a></details>}
      <p className="muted">{t.privateNote}</p>
    </div></div>
    {connection?.connected && <>
      <div className="panel"><span className="panel-label">{t.automation}</span><div className="panel-body">
        <p className="muted">{t.automationHint}</p>
        <form onSubmit={(event) => { event.preventDefault(); action("settings", async () => {
          await api("/youtube/settings", { method: "POST", body: JSON.stringify({ auto_publish: autoPublish, privacy_status: autoPrivacy, include_queued: includeQueued }) });
          setIncludeQueued(false); await refresh(); setMessage(t.settingsSaved);
        }); }}>
          <label className="checkbox-field"><input type="checkbox" checked={autoPublish} disabled={!!busy} onChange={(e) => setAutoPublish(e.target.checked)} />{t.enableAuto}</label>
          <label><span className="label">{t.privacy}</span><select aria-label={t.autoVisibility} value={autoPrivacy} onChange={(e) => setAutoPrivacy(e.target.value)}>{["private", "unlisted", "public"].map((id) => <option key={id} value={id}>{t[id]}</option>)}</select></label>
          {autoPublish && <label className="checkbox-field"><input type="checkbox" checked={includeQueued} disabled={!!busy} onChange={(e) => setIncludeQueued(e.target.checked)} />{t.includeQueued}</label>}
          <button className="btn" disabled={!!busy}>{t.saveSettings}</button>
        </form>
      </div></div>
      <div className="stepper">{t.uploadSteps.map((label, index) => <div className={`step ${step === index + 1 ? "step-now" : step > index + 1 ? "step-done" : ""}`} key={label}>
        <span className="step-dot">{index + 1}</span><span className="step-name">{label}</span></div>)}</div>
      {step === 1 && <><h2 className="retention-heading">{t.selectVideo}</h2>{!output.length && <p>{t.noOutput}</p>}
        <div className="gallery">{output.map((item) => <figure key={item.source + item.id}><video src={item.url} controls preload="metadata" />
          <figcaption><b>{item.title}</b><div className="job-actions"><button className="btn" disabled={!!busy} onClick={() => choose(item)}>{t.next}</button></div></figcaption></figure>)}</div></>}
      {step === 2 && selected && <div className="panel panel-narrow"><span className="panel-label">{t.details}</span><div className="panel-body">
        <form onSubmit={(event) => { event.preventDefault(); setStep(3); }}>
          <p className="muted">{t.metadataHint}</p>
          <button type="button" className="btn" disabled={!!busy} onClick={() => generateDetails(selected, true)}>{busy === "metadata" ? t.generatingMetadata : t.generateMetadata}</button>
          <fieldset disabled={!!busy} style={{ border: 0, padding: 0, margin: "16px 0 0", minWidth: 0 }}>
          <label><span className="label">{t.title}</span><input required maxLength={100} value={title} onChange={(e) => setTitle(e.target.value)} /><small className="muted">{t.titleHint}</small></label>
          <label><span className="label">{t.description}</span><textarea maxLength={5000} rows={5} value={description} onChange={(e) => setDescription(e.target.value)} /></label>
          <label><span className="label">{t.privacy}</span><select aria-label={t.privacy} value={privacy} onChange={(e) => setPrivacy(e.target.value)}>{["private", "unlisted", "public"].map((id) => <option key={id} value={id}>{t[id]}</option>)}</select></label>
          <label><span className="label">{t.tags}</span><input maxLength={400} value={tags} onChange={(e) => setTags(e.target.value)} /></label>
          <label className="checkbox-field"><input type="checkbox" checked={kids} onChange={(e) => setKids(e.target.checked)} />{t.kids}</label>
          <label className="checkbox-field"><input type="checkbox" checked={synthetic} onChange={(e) => setSynthetic(e.target.checked)} />{t.synthetic}</label><small className="muted">{t.syntheticHint}</small>
          <div className="job-actions"><button type="button" className="btn" onClick={() => setStep(1)}>{t.back}</button><button className="btn btn-primary">{t.review}</button></div>
          </fieldset>
        </form></div></div>}
      {step === 3 && selected && <div className="panel"><span className="panel-label">{t.review}</span><div className="panel-body">
        <video className="upload-preview" src={selected.url} controls preload="metadata" aria-label={t.preview} /><h2 className="retention-heading">{title}</h2>
        <p className="upload-description">{description}</p><p><b>{t.privacy}: {t[privacy]}</b> · {connection.channel_title}</p>
        {!!tags.trim() && <p className="muted">{t.tags}: {tags}</p>}
        {title.length > 60 && <p>{t.titleLong}</p>}{!description.trim() && <p>{t.descriptionEmpty}</p>}
        <div className="job-actions"><button className="btn" disabled={!!busy} onClick={() => setStep(2)}>{t.back}</button>
          <button className="btn btn-primary" disabled={!!busy || !title.trim()} onClick={upload}>{busy === "upload" ? t.uploading : t.upload}</button></div>
      </div></div>}
      <h2 className="retention-heading">{t.uploads}</h2>{uploads.length ? <div className="table-wrap"><table><tbody>{uploads.map((row) => <tr key={row.id}>
        <td>{row.title || row.id.slice(0, 8)}</td><td>{row.status}</td><td>{row.error || (row.url && <a href={row.url} target="_blank" rel="noreferrer">{t.openVideo}</a>)}</td></tr>)}</tbody></table></div> : <p>{t.emptyUploads}</p>}
      <div className="panel"><span className="panel-label">{t.analytics}</span><div className="panel-body">
        <p className="muted">{t.performanceHint}</p>
        <button className="btn" disabled={!!busy} onClick={() => action("sync", async () => {
          const result = await api("/youtube/sync", { method: "POST", timeoutMs: 360000 });
          setPerformance(await api("/youtube/performance")); setMessage(`${t.syncResult}: ${result.updated} · ${t.waitingData}: ${result.waiting} · ${t.syncFailed}: ${result.failed}`);
        })}>{busy === "sync" ? t.syncing : t.syncMetrics}</button>
        {performance.length > 0 && <div className="table-wrap"><table><thead><tr><th>{t.title}</th><th>{t.views}</th><th>{t.engagedViews}</th><th>{t.averageWatched}</th><th>{t.likes}</th><th>{t.comments}</th></tr></thead>
          <tbody>{performance.map((item) => <tr key={item.id}><td>{item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a> : item.title}</td>
            <td>{item.metrics.views ?? "—"}</td><td>{item.metrics.engagedViews ?? "—"}</td><td>{item.metrics.averageViewPercentage == null ? t.waitingData : `${Number(item.metrics.averageViewPercentage).toFixed(1)}%`}</td><td>{item.metrics.likes ?? "—"}</td><td>{item.metrics.comments ?? "—"}</td></tr>)}</tbody></table></div>}
        <button className="btn" disabled={!!busy} onClick={() => action("videos", async () => { const rows = await api("/youtube/videos"); setVideos(rows); setVideoId(rows[0]?.id || ""); })}>{t.loadVideos}</button>
        {videos?.length === 0 && <p>{t.noVideos}</p>}
        {!!videos?.length && <form onSubmit={(event) => { event.preventDefault(); action("analytics", async () => {
          const report = await api(`/youtube/retention/${videoId}?start=${start}&end=${end}`, { timeoutMs: 45000 });
          onRetention(report, videos.find((video) => video.id === videoId)?.title || videoId);
        }); }}>
          <label><span className="label">{t.selectVideo}</span><select aria-label={t.selectVideo} value={videoId} onChange={(e) => setVideoId(e.target.value)}>{videos.map((video) => <option key={video.id} value={video.id}>{video.title}</option>)}</select></label>
          <div className="insights-fields"><label><span className="label">{t.startDate}</span><input required type="date" value={start} max={end} onChange={(e) => setStart(e.target.value)} /></label>
            <label><span className="label">{t.endDate}</span><input required type="date" value={end} min={start} max={today()} onChange={(e) => setEnd(e.target.value)} /></label></div>
          <button className="btn btn-primary" disabled={!!busy}>{t.analyze}</button>
        </form>}
      </div></div>
    </>}
  </section>;
}
