import React, { useRef, useState } from "react";
import { api } from "../api.js";
import { useLang } from "../i18n.jsx";
import { INTEGRATIONS_COPY } from "../integrations-copy.js";
import { GENERATION_PROVIDERS } from "../generation.js";

export default function Ideas({ onReference }) {
  const { lang } = useLang(); const t = INTEGRATIONS_COPY[lang];
  const [topics, setTopics] = useState([]); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const seen = useRef([]);
  const [provider, setProvider] = useState("claude-code");
  async function load(chosen = provider) {
    setBusy(true); setError("");
    try {
      const out = await api("/ideas", { method: "POST", body: JSON.stringify({ language: lang, avoid: seen.current.slice(-20), llm_provider: chosen }) });
      seen.current = [...seen.current, ...out.topics]; setTopics(out.topics);
    } catch { setError(t.error); } finally { setBusy(false); }
  }
  return <section><p className="muted">{t.ideasIntro}</p>
    <label><span className="label">{t.provider}</span><select value={provider} disabled={busy} onChange={(e) => setProvider(e.target.value)}>
      {Object.entries(GENERATION_PROVIDERS).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
    <div style={{ marginTop: 20 }}><button className="btn" disabled={busy} onClick={() => load()}>{busy ? t.ideasLoading : topics.length ? t.ideasRegenerate : t.ideasGenerate}</button></div>
    {error && <p className="alarm-text" role="alert">{error}</p>}
    <div className="reference-results">{topics.map((topic) => <button className="choice" key={topic} disabled={busy} onClick={() => onReference({ label: topic })}>
      <b>{topic}</b><small>{t.ideasUse}</small></button>)}</div>
  </section>;
}
