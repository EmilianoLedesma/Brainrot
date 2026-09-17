import React, { useState } from "react";
import { useCopy } from "../i18n.jsx";
import { useReveal } from "./Home.jsx";

/* Copy comes from the translation tree as blocks, so code, commands, table keys
   and enum values stay identical in both languages. Backticks mark inline code. */

function inline(text) {
  return text.split("`").map((part, i) =>
    i % 2 ? <code key={i}>{part}</code> : <React.Fragment key={i}>{part}</React.Fragment>,
  );
}

function Block({ block }) {
  switch (block.type) {
    case "p":
      return <p>{inline(block.text)}</p>;
    case "ol":
      return (
        <ol className="steps-list">
          {block.items.map((item) => (
            <li key={item}>{inline(item)}</li>
          ))}
        </ol>
      );
    case "code":
      return <pre className="code">{block.text}</pre>;
    case "callout":
      return (
        <div className="callout">
          <b>{block.strong}</b> {inline(block.text)}
        </div>
      );
    case "table":
      return (
        <div className="table-wrap">
          <table className="doc-table">
            <thead>
              <tr>
                {block.head.map((cell) => (
                  <th key={cell}>{cell}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row) => (
                <tr key={row[0]}>
                  {row.map((cell, i) => (
                    <td key={i}>{inline(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    default:
      return null;
  }
}

export default function Docs() {
  const root = useReveal();
  const t = useCopy().docs;
  const [active, setActive] = useState(t.sections[0].id);

  return (
    <div ref={root} className="page">
      <header className="page-head">
        <span className="label">{t.label}</span>
        <h1>{t.title}</h1>
        <p className="lede">{t.lede}</p>
      </header>

      <div className="doc-layout">
        <aside className="doc-nav">
          {t.sections.map((section) => (
            <button
              key={section.id}
              className={active === section.id ? "active" : ""}
              onClick={() => {
                setActive(section.id);
                document
                  .getElementById(section.id)
                  ?.scrollIntoView({ behavior: "smooth", block: "start" });
              }}
            >
              {section.title}
            </button>
          ))}
        </aside>

        <div className="doc-body">
          {t.sections.map((section) => (
            <section className="doc-section reveal" id={section.id} key={section.id}>
              <h2>{section.title}</h2>
              {section.blocks.map((block, i) => (
                <Block block={block} key={i} />
              ))}
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
