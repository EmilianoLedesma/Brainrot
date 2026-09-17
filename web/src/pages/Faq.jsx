import React from "react";
import { go } from "../router.js";
import { useCopy } from "../i18n.jsx";
import { useReveal } from "./Home.jsx";

export default function Faq() {
  const root = useReveal();
  const t = useCopy().faq;

  return (
    <div ref={root} className="page">
      <header className="page-head">
        <span className="label">{t.label}</span>
        <h1>
          {t.titleA} <span className="serif">{t.titleB}</span>
        </h1>
        <p className="lede">{t.lede}</p>
      </header>

      {t.groups.map((group) => (
        <section className="faq-group reveal" key={group.title}>
          <h2>{group.title}</h2>
          <div className="faq-list">
            {group.items.map((item) => (
              <details key={item.q}>
                <summary>{item.q}</summary>
                <p>{item.a}</p>
              </details>
            ))}
          </div>
        </section>
      ))}

      <section className="section" style={{ paddingTop: 20 }}>
        <div className="cta reveal">
          <h2>
            {t.ctaTitle} <mark>{t.ctaMark}</mark>
          </h2>
          <p style={{ maxWidth: "46ch", margin: "0 auto 28px", fontWeight: 500 }}>
            {t.ctaBody}
          </p>
          <button className="btn btn-primary" onClick={() => go("docs")}>
            {t.ctaButton}
          </button>
        </div>
      </section>
    </div>
  );
}
