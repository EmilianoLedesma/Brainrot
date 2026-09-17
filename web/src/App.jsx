import React from "react";
import { go, useRoute } from "./router.js";
import { LangProvider, useLang } from "./i18n.jsx";
import Home from "./pages/Home.jsx";
import Docs from "./pages/Docs.jsx";
import Faq from "./pages/Faq.jsx";
import Workspace from "./pages/Workspace.jsx";

const PAGES = {
  home: Home,
  docs: Docs,
  faq: Faq,
  console: Workspace,
};

const STACK = ["FastAPI", "Supabase", "ffmpeg", "Claude", "edge-tts", "OpenCV"];

function LangToggle() {
  const { t, toggle } = useLang();
  return (
    <button className="btn lang-btn" onClick={toggle} title={t.langTitle}>
      <span aria-hidden="true">{t.langFlag}</span>
      {t.langButton}
    </button>
  );
}

function Footer() {
  const { t } = useLang();
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <span className="wordmark wordmark-static">Brainrot</span>
          <p>{t.footer.blurb}</p>
        </div>

        <nav className="footer-col">
          <h4>{t.footer.product}</h4>
          <button onClick={() => go("home")}>{t.footer.overview}</button>
          <button onClick={() => go("console")}>{t.footer.workspace}</button>
        </nav>

        <nav className="footer-col">
          <h4>{t.footer.resources}</h4>
          <button onClick={() => go("docs")}>{t.footer.docs}</button>
          <button onClick={() => go("faq")}>{t.footer.faq}</button>
        </nav>

        <div className="footer-col">
          <h4>{t.footer.builtWith}</h4>
          <ul className="stack-list">
            {STACK.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="footer-bar">
        <span>© {new Date().getFullYear()} Brainrot</span>
        <span>{t.footer.note}</span>
      </div>
    </footer>
  );
}

function Shell() {
  const route = useRoute();
  const { t } = useLang();
  const Page = PAGES[route] ?? Home;

  return (
    <div className="shell">
      <header className="topbar">
        <button className="wordmark" onClick={() => go("home")}>
          Brainrot
        </button>

        <nav className="tabs">
          <button aria-current={route === "home"} onClick={() => go("home")}>
            {t.nav.home}
          </button>
          <button aria-current={route === "docs"} onClick={() => go("docs")}>
            {t.nav.docs}
          </button>
          <button aria-current={route === "faq"} onClick={() => go("faq")}>
            {t.nav.faq}
          </button>
          <LangToggle />
          <button
            className="btn btn-primary nav-cta"
            aria-current={route === "console"}
            onClick={() => go("console")}
          >
            {t.nav.workspace}
          </button>
        </nav>
      </header>

      <Page />
      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <LangProvider>
      <Shell />
    </LangProvider>
  );
}
