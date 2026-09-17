import React, { useEffect, useRef } from "react";
import { go } from "../router.js";
import { useCopy } from "../i18n.jsx";

/* Captions in the hero reel stay untranslated on purpose: they stand in for the
   output of a real job, and a job's script is whatever language you asked for. */
const REEL = [
  "Octopuses have three hearts",
  "He said the quiet part",
  "AITA for keeping the money",
  "Rome ran on borrowed silver",
];

/** Adds `seen` to each `.reveal` element once it scrolls into view. */
export function useReveal() {
  const root = useRef(null);

  useEffect(() => {
    const targets = root.current?.querySelectorAll(".reveal") ?? [];
    // Without IntersectionObserver the content must still be visible, never stuck hidden.
    if (!("IntersectionObserver" in window)) {
      targets.forEach((el) => el.classList.add("seen"));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("seen");
            observer.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.1 },
    );
    targets.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return root;
}

export default function Home() {
  const root = useReveal();
  const t = useCopy().home;

  return (
    <div ref={root}>
      <section className="hero-wide">
        <div className="hero-copy">
          <div className="sticker-row rise" style={{ "--delay": "0.05s" }}>
            <span className="sticker sticker-lime tilt-l">{t.stickers[0]}</span>
            <span className="sticker sticker-pink tilt-r">{t.stickers[1]}</span>
            <span className="sticker tilt-l">{t.stickers[2]}</span>
          </div>

          <h1 className="rise" style={{ "--delay": "0.14s" }}>
            {t.titleA} <mark>{t.titleMark}</mark>
            <span className="serif">{t.titleB}</span>
          </h1>

          <p className="lede rise" style={{ "--delay": "0.3s" }}>
            {t.lede}
          </p>

          <div className="hero-actions rise" style={{ "--delay": "0.42s" }}>
            <button className="btn btn-primary" onClick={() => go("console")}>
              {t.ctaPrimary}
            </button>
            <button className="btn" onClick={() => go("docs")}>
              {t.ctaSecondary}
            </button>
          </div>
        </div>

        {/* Duplicated so the -50% scroll loops without a seam. */}
        <div className="phone rise" style={{ "--delay": "0.5s" }} aria-hidden="true">
          <div className="phone-rail">
            {[...REEL, ...REEL].map((caption, i) => (
              <div className="reel-card" key={i}>
                <span className="cap">{caption}</span>
              </div>
            ))}
          </div>
          <div className="phone-hud">
            <span className="rec">Live</span>
            <span className="label">1080 × 1920</span>
          </div>
        </div>
      </section>

      <section className="section reveal">
        <div className="specs">
          {t.specs.map((spec) => (
            <div className="spec" key={spec.label}>
              <b>{spec.value}</b>
              <span className="label">{spec.label}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="section reveal" id="pipeline">
        <span className="label">{t.lineLabel}</span>
        <h2>
          {t.lineTitleA} <span className="serif">{t.lineTitleB}</span>
        </h2>
        <div className="pipeline">
          {t.stages.map((stage, i) => (
            <div className="stage" key={stage.no} style={{ "--delay": `${i * 0.5}s` }}>
              <span className="stage-no">{stage.no}</span>
              <b>{stage.name}</b>
              <small>{stage.note}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="section reveal">
        <span className="label">{t.intakeLabel}</span>
        <h2>
          {t.intakeTitleA} <span className="serif">{t.intakeTitleB}</span>
        </h2>
        <div className="sources">
          {t.sources.map((source) => (
            <article className="source" key={source.idx}>
              <span className={`kind-tag kind-${source.kind}`}>{source.idx}</span>
              <h3>{source.title}</h3>
              <p>{source.blurb}</p>
              <ul>
                {source.points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="section reveal">
        <span className="label">{t.releaseLabel}</span>
        <h2>
          {t.releaseTitleA} <span className="serif">{t.releaseTitleMid}</span>{" "}
          {t.releaseTitleB}
        </h2>
        <p className="lede" style={{ maxWidth: "62ch", marginBottom: 34 }}>
          {t.releaseBody}
        </p>
        <button className="btn" onClick={() => go("faq")}>
          {t.releaseCta}
        </button>
      </section>

      <section className="section" style={{ paddingTop: 0 }}>
        <div className="cta reveal">
          <h2>
            {t.finalTitleA} <mark>{t.finalMark}</mark>
          </h2>
          <button className="btn btn-primary" onClick={() => go("console")}>
            {t.finalCta}
          </button>
        </div>
      </section>
    </div>
  );
}
