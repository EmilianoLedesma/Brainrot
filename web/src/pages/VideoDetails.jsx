import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { useLang } from "../i18n.jsx";
import { INTEGRATIONS_COPY } from "../integrations-copy.js";
import Insights, { newInsightsSession } from "./Insights.jsx";

function date(offset = 0) { const value = new Date(); value.setDate(value.getDate() + offset); return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`; }

export default function VideoDetails({ assets, initialAssetId, videoSessions, onVideoSessionsChange }) {
  const { lang } = useLang(); const t = INTEGRATIONS_COPY[lang];
  const [selected, setSelected] = useState(initialAssetId || assets[0]?.id);
  const [localSessions, setLocalSessions] = useState({});
  const cache = videoSessions || localSessions; const setCache = onVideoSessionsChange || setLocalSessions;
  const [start, setStart] = useState(date(-28)); const [end, setEnd] = useState(date());
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  useEffect(() => { if (initialAssetId) setSelected(initialAssetId); }, [initialAssetId]);
  const asset = assets.find((item) => item.id === selected) || assets[0];
  const key = asset ? `${asset.source}:${asset.id}` : "";
  useEffect(() => { setError(""); }, [key]);
  useEffect(() => {
    if (!key || !asset?.subtitles) return;
    setCache((previous) => previous[key] ? previous : { ...previous, [key]: { ...newInsightsSession(), srt: asset.subtitles, srtName: t.savedCaptions } });
  }, [key, asset?.subtitles]);
  if (!asset) return null;
  const session = cache[key] || newInsightsSession();
  function updateSession(update) {
    setCache((previous) => ({ ...previous, [key]: typeof update === "function" ? update(previous[key] || newInsightsSession()) : update }));
  }
  const youtube = (asset.publications || []).find((row) => row.platform === "youtube");
  const metrics = youtube?.analytics || {};
  async function loadRetention(event) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const report = await api(`/youtube/retention/${youtube.video_id}?start=${start}&end=${end}`, { timeoutMs: 45000 });
      updateSession((previous) => ({ ...previous, report, step: 2, csvName: `YouTube · ${asset.title}` }));
    } catch (exception) { setError(exception.status === 422 ? exception.message : t.error); }
    finally { setBusy(false); }
  }
  return <section className="video-details" aria-label={t.videoDetails}>
    {assets.length > 1 && <label><span className="label">{t.selectVideo}</span><select aria-label={t.selectVideo} disabled={busy} value={asset.id} onChange={(event) => setSelected(event.target.value)}>
      {assets.map((item) => <option value={item.id} key={item.id}>{item.title}</option>)}
    </select></label>}
    <div className="video-detail-layout"><video key={asset.id} className="detail-player" src={asset.url} controls preload="metadata" aria-label={t.preview}
      onLoadedMetadata={(event) => { const seconds = event.currentTarget.duration; if (Number.isFinite(seconds) && seconds > 0) updateSession((previous) => previous.duration ? previous : { ...previous, duration: String(Number(seconds.toFixed(2))) }); }} />
      <div><h2 className="retention-heading">{asset.title}</h2><p className="muted">{asset.source} · {asset.created_at ? new Date(asset.created_at).toLocaleString() : ""}</p>
        <p>{t.localVideo}</p>{asset.source_url && <a href={asset.source_url} target="_blank" rel="noreferrer">{t.source}</a>}
        <h3>{t.uploads}</h3>{youtube ? <><p><span className={`status status-${youtube.status}`}>{youtube.status}</span> · {t[youtube.metadata?.privacy_status] || "YouTube"}</p>
          {youtube.url && <a href={youtube.url} target="_blank" rel="noreferrer">{t.openVideo}</a>}
          {youtube.metadata?.title && <p><b>{youtube.metadata.title}</b></p>}
          {youtube.metadata?.description && <p className="upload-description">{youtube.metadata.description}</p>}
          {!!youtube.metadata?.tags?.length && <p className="muted">{youtube.metadata.tags.join(" · ")}</p>}
        </> : <p className="muted">{t.noYoutubeUpload}</p>}
        <dl className="execution-facts">{[[t.views, metrics.views], [t.engagedViews, metrics.engagedViews], [t.likes, metrics.likes], [t.comments, metrics.comments],
          [t.averageWatched, metrics.averageViewPercentage == null ? null : `${Number(metrics.averageViewPercentage).toFixed(1)}%`]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value ?? "—"}</dd></div>)}</dl>
        {metrics.end_date ? <p className="muted">{t.metricsThrough}: {metrics.end_date}</p> : <p className="muted">{t.waitingData}</p>}
      </div></div>
    <details className="video-narration"><summary>{t.savedScript}</summary><p className="upload-description">{asset.narration || t.noSavedScript}</p></details>
    <h3 className="execution-subhead">{t.videoInsights}</h3><p className="muted">{t.performanceHint}</p>
    {youtube?.status === "published" && youtube.video_id && <form onSubmit={loadRetention}>
      <div className="insights-fields"><label><span className="label">{t.startDate}</span><input type="date" required max={end} value={start} onChange={(event) => setStart(event.target.value)} /></label>
        <label><span className="label">{t.endDate}</span><input type="date" required min={start} max={date()} value={end} onChange={(event) => setEnd(event.target.value)} /></label></div>
      <button className="btn" disabled={busy}>{busy ? t.syncing : t.loadVideoRetention}</button>
    </form>}
    {error && <p role="alert" className="alarm-text">{error}</p>}
    <Insights insightSession={session} onInsightSessionChange={updateSession} />
  </section>;
}
