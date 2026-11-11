import React, { useEffect, useRef, useState } from "react";
import { useLang } from "../i18n.jsx";
import { INTEGRATIONS_COPY } from "../integrations-copy.js";
import YouTube from "./YouTube.jsx";
import Insights, { newInsightsSession } from "./Insights.jsx";

// The hub for connected accounts: each platform's connection, and the performance of every video by platform.
// Instagram and TikTok are placeholders until their publishing and metrics integrations exist.
const SOON = ["instagram", "tiktok"];

export default function Accounts() {
  const { lang } = useLang();
  const t = INTEGRATIONS_COPY[lang];
  const [insightSession, setInsightSession] = useState(newInsightsSession);
  const insightRef = useRef(null);
  useEffect(() => { if (insightSession.report) insightRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [insightSession.report]);

  return (
    <div className="page">
      <header className="page-head">
        <span className="label">{t.accountsLabel}</span>
        <h1>{t.accountsTitle}</h1>
      </header>
      <p className="muted">{t.accountsIntro}</p>
      <YouTube onRetention={(report, title) => setInsightSession({ ...newInsightsSession(), report, csvName: `YouTube · ${title}`, step: 2 })}>
        {SOON.map((id) => (
          <div className="panel account-card account-card-soon" key={id}><div className="panel-body">
            <div className="account-head"><h2>{t.platforms[id]}</h2><span className="badge">{t.soon}</span></div>
            <p className="muted">{t.soonHint[id]}</p>
            <div className="job-actions"><button className="btn" disabled>{t.connectPlatform(t.platforms[id])}</button></div>
          </div></div>
        ))}
      </YouTube>
      {insightSession.report && <div ref={insightRef}><Insights insightSession={insightSession} onInsightSessionChange={setInsightSession} /></div>}
    </div>
  );
}
